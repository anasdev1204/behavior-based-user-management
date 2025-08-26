from __future__ import annotations
import argparse, os, time
from pathlib import Path
import yaml
from src.utils.logging import setup_logging
from src.utils.storage import EventStore

def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dirs(cfg: dict):
    for key in ("data_dir","raw_dir","interim_dir","processed_dir","models_dir","logs_dir"):
        Path(cfg["paths"][key]).mkdir(parents=True, exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description="Bootstrap behav-id project")
    parser.add_argument("--init", action="store_true", help="Initialize folders & DB")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    ensure_dirs(cfg)
    logger = setup_logging(cfg["paths"]["logs_dir"])

    if args.init:
        db_path = cfg["paths"]["db_path"]
        store = EventStore(db_path)
        store.create_schema()
        # create a placeholder session row (optional)
        session_id = f"bootstrap_{int(time.time()*1e6):d}"
        store.upsert_session(
            session_id=session_id,
            user_label=None,
            device_hash=None,
            os=cfg["system"].get("os_target","unknown"),
            context="bootstrap",
            start_ts_ns=int(time.time_ns()),
            end_ts_ns=None,
        )
        store.close()
        logger.info("Initialized DB schema at %s", db_path)
    else:
        logger.info("No action. Use --init to create schema.")

if __name__ == "__main__":
    main()
