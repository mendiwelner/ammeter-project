import yaml
from typing import Dict


def load_config(config_path: str) -> Dict:
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
    except FileNotFoundError as exc:
        raise ValueError(f"Configuration file not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML configuration: {config_path}") from exc

    if not isinstance(config, dict):
        raise ValueError("Configuration must contain a YAML mapping")
    return config
