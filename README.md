# Ammeter Emulators

This project provides emulators for different types of ammeters: Greenlee, ENTES, and CIRCUTOR. Each ammeter emulator runs on a separate thread and can respond to current measurement requests.

## Project Structure

- `Ammeters/`
  - `Circutor_Ammeter.py`: Emulator for the CIRCUTOR ammeter.
  - `Entes_Ammeter.py`: Emulator for the ENTES ammeter.
  - `Greenlee_Ammeter.py`: Emulator for the Greenlee ammeter.
  - `base_ammeter.py`: Base class for all ammeter emulators.
  - `client.py`: Client to request current measurements from the ammeter emulators.
- `config/`
  - `config.yaml`: Configuration file for the ammeter emulators.
- `examples/`
  - `run_tests.py`: Example test runner.
- `main.py`: Starts the emulators and runs the complete test suite.
- `src/`
  - `testing/`
    - `test_framework.py`: Configurable sampling, statistical analysis, and result archiving.
  - `utils/`
    - `config.py`: Configuration settings.
    - `logger.py`: Logging setup.
    - `Utils.py`: Utility functions, including `generate_random_float`.

## Usage

# Ammeter Emulators

## Greenlee Ammeter

- **Port**: 5000
- **Command**: `MEASURE_GREENLEE -get_measurement`
- **Measurement Logic**: Calculates current using voltage (1V - 10V) and (0.1Ω - 100Ω).
- **Measurement method** : Ohm's Law: I = V / R

## ENTES Ammeter

- **Port**: 5001
- **Command**: `MEASURE_ENTES -get_data`
- **Measurement Logic**: Calculates current using magnetic field strength (0.01T - 0.1T) and calibration factor (500 - 2000).
- **Measurement method** : Hall Effect: I = B * K

## CIRCUTOR Ammeter

- **Port**: 5002
- **Command**: `MEASURE_CIRCUTOR -get_measurement`
- **Measurement Logic**: Calculates current using voltage values (0.1V - 1.0V) over a number of samples and a random time step (0.001s - 0.01s).
- **Measurement method** : Rogowski Coil Integration: I = ∫V dt

Install the dependencies and start the complete test run:
```sh
python -m pip install -r requirements.txt
python main.py
```

The default run collects five measurements from each ammeter at 2 Hz. Results are written
as JSON files under `results/`. Sampling and archive settings are configured in
`config/config.yaml`.

Bonus analysis is also available from the same run: accuracy and consistency comparison,
optional measurement plots, and configurable error simulation. Install the dependencies from
`requirements.txt` before enabling plots.

Accuracy requires a known reference current. Set `analysis.reference_current_a` in
`config/config.yaml`; when it is `null`, the report deliberately omits accuracy claims and
reports consistency only.

The implementation details, fixes, and validation steps are documented in
[`documentation.md`](documentation.md).