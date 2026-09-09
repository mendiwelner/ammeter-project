import json
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.config import load_config
from Ammeters.client import request_current_from_ammeter


class AmmeterTestFramework:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_config(config_path)

    def run_test(self, ammeter_type: str) -> Dict:
        ammeter = self.config.get("ammeters", {}).get(ammeter_type)
        if not ammeter:
            raise ValueError(f"Unknown ammeter type: {ammeter_type}")

        sampling = self.config.get("testing", {}).get("sampling", {})
        count = sampling.get("measurements_count")
        duration = sampling.get("total_duration_seconds")
        frequency = sampling.get("sampling_frequency_hz")
        if count is None and duration is None:
            count = 10
        if count is not None and count < 1:
            raise ValueError("measurements_count must be positive")
        if duration is not None and duration <= 0:
            raise ValueError("total_duration_seconds must be positive")
        if frequency is not None and frequency <= 0:
            raise ValueError("sampling_frequency_hz must be positive")

        measurements: List[float] = []
        started_at_utc = datetime.now(timezone.utc).isoformat()
        started_at = time.monotonic()
        interval = 1.0 / frequency if frequency else 0.0
        next_sample = started_at
        while (count is None or len(measurements) < count) and (
            duration is None or time.monotonic() - started_at < duration
        ):
            self._simulate_error_if_configured()
            measurements.append(request_current_from_ammeter(
                int(ammeter["port"]),
                str(ammeter["command"]).encode("utf-8"),
            ))
            if interval:
                next_sample += interval
                time.sleep(max(0.0, next_sample - time.monotonic()))

        if not measurements:
            raise RuntimeError(f"No measurements collected for {ammeter_type}")

        result = {
            "test_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
            "ammeter_type": ammeter_type,
            "measurements": measurements,
            "statistics": {
                "mean": statistics.fmean(measurements),
                "median": statistics.median(measurements),
                "standard_deviation": statistics.stdev(measurements) if len(measurements) > 1 else 0.0,
                "minimum": min(measurements),
                "maximum": max(measurements),
                "range": max(measurements) - min(measurements),
                "coefficient_of_variation": self._coefficient_of_variation(measurements),
            },
            "measurement_count": len(measurements),
            "started_at_utc": started_at_utc,
        }
        self._archive_result(result)
        return result

    def compare_results(
        self,
        results: Dict[str, Dict],
        reference_current_a: Optional[float] = None,
    ) -> Dict:
        """Compare accuracy against a reference and precision across devices."""
        if not results:
            raise ValueError("At least one result is required for comparison")

        means = [result["statistics"]["mean"] for result in results.values()]
        comparison_reference = reference_current_a

        devices = {}
        for ammeter_type, result in results.items():
            stats = result["statistics"]
            mean = stats["mean"]
            coefficient = stats.get(
                "coefficient_of_variation",
                self._coefficient_of_variation(result["measurements"]),
            )
            devices[ammeter_type] = {
                "mean_current_a": mean,
                "standard_deviation_a": stats["standard_deviation"],
                "coefficient_of_variation": coefficient,
            }
            if comparison_reference is not None:
                absolute_error = abs(mean - comparison_reference)
                relative_error = absolute_error / abs(comparison_reference) if comparison_reference else 0.0
                devices[ammeter_type].update({
                    "absolute_error_a": absolute_error,
                    "relative_error_percent": relative_error * 100,
                })

        most_consistent = min(
            devices,
            key=lambda name: devices[name]["coefficient_of_variation"],
        )
        most_accurate = (
            min(devices, key=lambda name: devices[name]["absolute_error_a"])
            if comparison_reference is not None
            else None
        )
        comparison = {
            "comparison_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
            "reference_current_a": comparison_reference,
            "accuracy_available": comparison_reference is not None,
            "devices": devices,
            "most_consistent_ammeter": most_consistent,
            "most_accurate_ammeter": most_accurate,
        }
        self._archive_comparison(comparison)
        return comparison

    def generate_visualizations(self, results: Dict[str, Dict]) -> List[str]:
        visualization = self.config.get("analysis", {}).get("visualization", {}) or {}
        if not visualization.get("enabled", False):
            return []

        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise RuntimeError(
                "Visualization requires matplotlib; install requirements.txt"
            ) from exc

        output_directory = Path(
            visualization.get("directory", self.config.get("result_management", {}).get("directory", "results"))
        )
        output_directory.mkdir(parents=True, exist_ok=True)
        plot_types = visualization.get("plot_types", ["line", "boxplot", "histogram", "rolling_mean"])
        paths = []
        if "line" in plot_types:
            figure, axis = plt.subplots()
            for ammeter_type, result in results.items():
                axis.plot(range(1, len(result["measurements"]) + 1), result["measurements"], marker="o", label=ammeter_type)
            axis.set(title="Ammeter measurements", xlabel="Sample", ylabel="Current (A)")
            axis.legend()
            line_path = output_directory / "measurements_line.png"
            figure.savefig(line_path, bbox_inches="tight")
            plt.close(figure)
            paths.append(str(line_path))

        if "boxplot" in plot_types:
            figure, axis = plt.subplots()
            labels = list(results)
            axis.boxplot([results[name]["measurements"] for name in labels], tick_labels=labels)
            axis.set(title="Ammeter measurement distribution", ylabel="Current (A)")
            boxplot_path = output_directory / "measurements_boxplot.png"
            figure.savefig(boxplot_path, bbox_inches="tight")
            plt.close(figure)
            paths.append(str(boxplot_path))

        if "histogram" in plot_types:
            figure, axis = plt.subplots()
            for ammeter_type, result in results.items():
                axis.hist(result["measurements"], bins=visualization.get("histogram_bins", 10), alpha=0.5, label=ammeter_type)
            axis.set(title="Ammeter measurement distribution", xlabel="Current (A)", ylabel="Frequency")
            axis.legend()
            histogram_path = output_directory / "measurements_histogram.png"
            figure.savefig(histogram_path, bbox_inches="tight")
            plt.close(figure)
            paths.append(str(histogram_path))

        if "rolling_mean" in plot_types:
            figure, axis = plt.subplots()
            window = int(visualization.get("rolling_window", 3))
            if window < 1:
                raise ValueError("visualization.rolling_window must be positive")
            for ammeter_type, result in results.items():
                measurements = result["measurements"]
                rolling_means = [
                    statistics.fmean(measurements[max(0, index - window + 1): index + 1])
                    for index in range(len(measurements))
                ]
                axis.plot(range(1, len(rolling_means) + 1), rolling_means, label=ammeter_type)
            axis.set(title="Rolling mean of measurements", xlabel="Sample", ylabel="Current (A)")
            axis.legend()
            rolling_path = output_directory / "measurements_rolling_mean.png"
            figure.savefig(rolling_path, bbox_inches="tight")
            plt.close(figure)
            paths.append(str(rolling_path))
        return paths

    def _simulate_error_if_configured(self) -> None:
        simulation = self.config.get("testing", {}).get("error_simulation", {}) or {}
        if not simulation.get("enabled", False):
            return
        probability = float(simulation.get("probability", 0.0))
        if not 0 <= probability <= 1:
            raise ValueError("error_simulation.probability must be between 0 and 1")
        if random.random() >= probability:
            return
        error_type = simulation.get("error_type", "measurement_error")
        if error_type == "timeout":
            raise TimeoutError("Simulated ammeter timeout")
        raise RuntimeError("Simulated measurement error")

    @staticmethod
    def _coefficient_of_variation(measurements: List[float]) -> float:
        mean = statistics.fmean(measurements)
        return statistics.stdev(measurements) / abs(mean) if len(measurements) > 1 and mean else 0.0

    def _archive_result(self, result: Dict) -> None:
        management = self.config.get("result_management", {}) or {}
        directory = Path(management.get("directory", "results"))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{result['test_id']}_{result['ammeter_type']}.json"
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    def _archive_comparison(self, comparison: Dict) -> None:
        management = self.config.get("result_management", {}) or {}
        directory = Path(management.get("directory", "results"))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{comparison['comparison_id']}_comparison.json"
        path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")