from __future__ import annotations
from pathlib import Path
import yaml

def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dirs(cfg: dict):
    for key in ("data_dir","raw_dir","interim_dir","processed_dir","models_dir","logs_dir"):
        Path(cfg["paths"][key]).mkdir(parents=True, exist_ok=True)
