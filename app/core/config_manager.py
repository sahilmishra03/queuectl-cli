import json
import os

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".queuectl", "config.json")

DEFAULT_CONFIG = {
    "max-retries": 3,
    "backoff-base": 2,
}


def _ensure_config_dir():
    config_dir = os.path.dirname(CONFIG_PATH)
    os.makedirs(config_dir, exist_ok=True)


def load_config() -> dict:
    _ensure_config_dir()

    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    _ensure_config_dir()

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get(key: str):
    config = load_config()
    return config.get(key, DEFAULT_CONFIG.get(key))


def set_value(key: str, value: str) -> None:
    config = load_config()

    if key not in DEFAULT_CONFIG:
        raise ValueError(
            f"Unknown config key: '{key}'. "
            f"Valid keys: {', '.join(DEFAULT_CONFIG.keys())}"
        )

    # Cast to proper type based on default
    default_val = DEFAULT_CONFIG[key]
    if isinstance(default_val, int):
        config[key] = int(value)
    elif isinstance(default_val, float):
        config[key] = float(value)
    else:
        config[key] = value

    save_config(config)
