import os
from dataclasses import dataclass

from inim.prime.native.const import Panel

@dataclass(frozen=True)
class Config:
    host: str
    password: str
    pin: str | None
    port: int
    use_outer_frame: bool
    poll: float
    firmware: str | None

def get_yaml_config() -> Config:
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "config.yaml"
    )

    cfg: dict = {}
    if os.path.exists(config_path):
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}

    host = cfg.get("host", "")
    if not host:
        raise ValueError("Missing required config value: 'host'")

    return Config(
        host = host,
        password=cfg.get("password", Panel.DEFAULT_PASSWORD),
        pin=cfg.get("pin"),
        port=cfg.get("port", Panel.DEFAULT_PORT),
        use_outer_frame=cfg.get("use_outer_frame", False),
        poll=cfg.get("poll", 1.0),
        firmware = str(cfg["firmware"]) if cfg.get("firmware") is not None else None,
    )

def list_files(directory: str, extensions: list[str]) -> list[str]:
    extensions = {ext.lower() for ext in extensions}
    return [
        f for f in os.listdir(directory)
        if f.lower().endswith(tuple(extensions))
        and os.path.isfile(os.path.join(directory, f))
    ]

def choose_from_list(items: list[str], prompt: str = "Available options:") -> str | None:
    if not items:
        print("No options available.")
        return None
    print(f"{prompt}\n")
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")
    while True:
        try:
            choice = int(input("\nSelect a number: "))
            if 1 <= choice <= len(items):
                return items[choice - 1]
        except ValueError:
            pass
        print("Invalid selection, try again.")