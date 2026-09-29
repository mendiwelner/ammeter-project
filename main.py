import threading
import time

from Ammeters.Circutor_Ammeter import CircutorAmmeter
from Ammeters.Entes_Ammeter import EntesAmmeter
from Ammeters.Greenlee_Ammeter import GreenleeAmmeter
from src.testing.test_framework import AmmeterTestFramework


def run_greenlee_emulator():
    greenlee = GreenleeAmmeter(5000)
    greenlee.start_server()

def run_entes_emulator():
    entes = EntesAmmeter(5001)
    entes.start_server()

def run_circutor_emulator():
    circutor = CircutorAmmeter(5002)
    circutor.start_server()

def main():
    # Start each ammeter in a separate thread
    threading.Thread(target=run_greenlee_emulator, daemon=True).start()
    threading.Thread(target=run_entes_emulator, daemon=True).start()
    threading.Thread(target=run_circutor_emulator, daemon=True).start()

    time.sleep(0.5)
    framework = AmmeterTestFramework()
    results = {}
    for ammeter_type in framework.config.get("ammeters", {}):
        try:
            result = framework.run_test(ammeter_type)
        except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
            print(f"{ammeter_type}: test failed: {exc}")
            continue
        results[ammeter_type] = result
        metrics = result["statistics"]
        print(
            f"{ammeter_type}: {result['measurement_count']} measurements, "
            f"mean={metrics['mean']:.6f} A, "
            f"median={metrics['median']:.6f} A, "
            f"stddev={metrics['standard_deviation']:.6f} A, "
            f"min={metrics['minimum']:.6f} A, max={metrics['maximum']:.6f} A"
        )

    if not results:
        raise RuntimeError("No ammeter tests completed successfully")

    analysis = framework.config.get("analysis", {}) or {}
    comparison = framework.compare_results(
        results,
        reference_current_a=analysis.get("reference_current_a"),
    )
    plot_paths = framework.generate_visualizations(results)
    print(f"Most consistent ammeter: {comparison['most_consistent_ammeter']}")
    if comparison["accuracy_available"]:
        print(f"Most accurate ammeter: {comparison['most_accurate_ammeter']}")
    else:
        print("Most accurate ammeter: unavailable (configure reference_current_a)")
    if plot_paths:
        print(f"Generated plots: {', '.join(plot_paths)}")


if __name__ == "__main__":
    main()
