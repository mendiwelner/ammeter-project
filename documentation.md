# Ammeter Testing Documentation

## What was implemented

The project now provides one test API for Greenlee, ENTES, and CIRCUTOR. A test can be
limited by measurement count, total duration, or sampling frequency. Each run returns the
raw measurements and these metrics:

- mean
- median
- standard deviation
- minimum
- maximum

Every run receives a UTC identifier and is archived as a JSON file in the directory from
`result_management.directory` (default: `results/`).

Accuracy comparison is only reported when `analysis.reference_current_a` contains a known
reference current. Without that reference, the framework reports precision/consistency but
does not incorrectly label a device as the most accurate.

Visualization is configuration-driven through `analysis.visualization`. The framework can
generate raw measurement lines, boxplots, histograms, and rolling-mean plots. Histogram bin
count and rolling-mean window are configurable without code changes.

## Error handling

- Missing or malformed YAML configuration raises a clear `ValueError` before testing starts.
- Invalid client arguments, connection failures, socket timeouts, empty responses, malformed
   responses, and non-finite measurements are reported with an `AmmeterClientError` or a clear
   validation error.
- A failure of one ammeter is printed and does not prevent the remaining ammeters from being
   tested. If every ammeter fails, the run exits with an explicit error.
- Error simulation remains available for testing timeout and measurement-failure paths.

## Fixes made

1. `main.py` used ports 5001-5003 while the documented device configuration used 5000-5002.
   The ports are now consistent across the entry point and `config/config.yaml`.
2. `main.py` sent no requests and ended with `pass`. It now starts all three daemon servers,
   waits for startup, runs the configured test for each ammeter, and prints a summary.
3. The client only printed server responses. It now returns a validated `float` and raises a
   useful error for an empty or malformed response.
4. `src/testing/test_framework.py` was a stub. It now validates configuration, samples through
   the existing socket protocol, calculates statistics, and archives results.
5. The CIRCUTOR command in configuration now matches the emulator's complete command,
   including `-current`.

## Installation

Run from the repository root:

```sh
python -m pip install -r requirements.txt
```

No additional library was installed during implementation. The framework uses Python's
standard library for timing, statistics, JSON, and file handling, and PyYAML for the existing
configuration loader. The requirements file also retains the project's optional analysis and
visualization dependencies.

## Running

```sh
python main.py
```

The command starts the emulators and writes three result files under `results/`. To change the
sampling policy, edit `config/config.yaml`. Set `measurements_count` to `null` when using a
duration-only run; set `total_duration_seconds` to `null` for count-only sampling.

## Validation

Run the focused automated tests with:

```sh
python -m pytest -q
```

Alternatively, without pytest:

```sh
python -m unittest discover -s tests -v
```

Both commands run the same tests, which verify measurement collection, statistics, JSON
archiving, comparison behavior with and without a reference, error simulation, visualization,
and rejection of an unknown ammeter type. The end-to-end command also verifies the real socket
connection to all three emulators.