import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.testing.test_framework import AmmeterTestFramework


class AmmeterTestFrameworkTests(unittest.TestCase):
    def make_config(self, directory: str) -> Path:
        path = Path(directory) / "config.yaml"
        config = """testing:
  sampling:
    measurements_count: 3
    total_duration_seconds: null
    sampling_frequency_hz: null
ammeters:
  greenlee:
    port: 5000
    command: MEASURE_GREENLEE -get_measurement
result_management:
  directory: {directory}/results
""".replace("{directory}", directory.replace("\\", "/"))
        path.write_text(config, encoding="utf-8")
        return path

    @patch("src.testing.test_framework.request_current_from_ammeter", return_value=2.0)
    def test_collects_statistics_and_archives_result(self, request):
        with tempfile.TemporaryDirectory() as directory:
            framework = AmmeterTestFramework(str(self.make_config(directory)))
            result = framework.run_test("greenlee")

            self.assertEqual(result["measurement_count"], 3)
            self.assertEqual(result["statistics"]["mean"], 2.0)
            self.assertEqual(result["statistics"]["standard_deviation"], 0.0)
            self.assertEqual(request.call_count, 3)
            request.assert_called_with(5000, b"MEASURE_GREENLEE -get_measurement")

            archived = list((Path(directory) / "results").glob("*.json"))
            self.assertEqual(len(archived), 1)
            self.assertEqual(json.loads(archived[0].read_text())["test_id"], result["test_id"])

    def test_rejects_unknown_ammeter(self):
        with tempfile.TemporaryDirectory() as directory:
            framework = AmmeterTestFramework(str(self.make_config(directory)))
            with self.assertRaises(ValueError):
                framework.run_test("unknown")

    def test_compares_accuracy_and_consistency(self):
        with tempfile.TemporaryDirectory() as directory:
            framework = AmmeterTestFramework(str(self.make_config(directory)))
            results = {
                "greenlee": {
                    "measurements": [1.9, 2.0, 2.1],
                    "statistics": {
                        "mean": 2.0,
                        "standard_deviation": 0.1,
                        "coefficient_of_variation": 0.05,
                    },
                },
                "entes": {
                    "measurements": [1.0, 3.0, 2.0],
                    "statistics": {
                        "mean": 2.0,
                        "standard_deviation": 1.0,
                        "coefficient_of_variation": 0.5,
                    },
                },
            }

            comparison = framework.compare_results(results, reference_current_a=2.0)

            self.assertEqual(comparison["most_accurate_ammeter"], "greenlee")
            self.assertEqual(comparison["most_consistent_ammeter"], "greenlee")
            self.assertEqual(comparison["devices"]["entes"]["relative_error_percent"], 0.0)

    def test_does_not_claim_accuracy_without_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            framework = AmmeterTestFramework(str(self.make_config(directory)))
            results = {
                "greenlee": {
                    "measurements": [1.0, 1.1, 0.9],
                    "statistics": {
                        "mean": 1.0,
                        "standard_deviation": 0.1,
                        "coefficient_of_variation": 0.1,
                    },
                },
                "entes": {
                    "measurements": [2.0, 2.1, 1.9],
                    "statistics": {
                        "mean": 2.0,
                        "standard_deviation": 0.1,
                        "coefficient_of_variation": 0.05,
                    },
                },
            }

            comparison = framework.compare_results(results)

            self.assertFalse(comparison["accuracy_available"])
            self.assertIsNone(comparison["most_accurate_ammeter"])
            self.assertNotIn("absolute_error_a", comparison["devices"]["greenlee"])

    @patch("src.testing.test_framework.random.random", return_value=0.0)
    @patch("src.testing.test_framework.request_current_from_ammeter", return_value=2.0)
    def test_can_simulate_measurement_errors(self, request, random_value):
        with tempfile.TemporaryDirectory() as directory:
            framework = AmmeterTestFramework(str(self.make_config(directory)))
            framework.config["testing"]["error_simulation"] = {
                "enabled": True,
                "probability": 1.0,
                "error_type": "timeout",
            }

            with self.assertRaises(TimeoutError):
                framework.run_test("greenlee")
            request.assert_not_called()

    def test_generates_visualizations(self):
        with tempfile.TemporaryDirectory() as directory:
            framework = AmmeterTestFramework(str(self.make_config(directory)))
            framework.config["analysis"] = {
                "visualization": {
                    "enabled": True,
                    "directory": f"{directory}/plots",
                    "plot_types": ["line", "boxplot", "histogram", "rolling_mean"],
                    "histogram_bins": 5,
                    "rolling_window": 2,
                }
            }
            results = {
                "greenlee": {"measurements": [1.0, 1.1, 0.9]},
                "entes": {"measurements": [2.0, 2.1, 1.9]},
            }

            paths = framework.generate_visualizations(results)

            self.assertEqual(len(paths), 4)
            self.assertTrue(all(Path(path).is_file() for path in paths))


if __name__ == "__main__":
    unittest.main()