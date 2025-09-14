from __future__ import annotations
from pathlib import Path
from src.utils.logging import setup_logging
from src.utils.storage import EventStore
from src.utils.config import load_config, ensure_dirs
import argparse, time, uuid


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
        store = EventStore(db_path, logger)
        store.create_schema()
        session_id = str(uuid.uuid4())
        store.upsert_session(
            session_id=session_id,
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
