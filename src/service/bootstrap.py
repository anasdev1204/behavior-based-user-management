from __future__ import annotations
from pathlib import Path
from src.utils.logging import setup_logging
from src.utils.storage import EventStore
from src.utils.config import load_config, ensure_dirs
import argparse, time, uuid, yaml


def main():
    parser = argparse.ArgumentParser(description="Bootstrap project")
    parser.add_argument("--init", action="store_true", help="Initialize folders & DB")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--label", action="store", help="Label that will be used in the DB")
    args = parser.parse_args()

    cfg = load_config(args.config)
    ensure_dirs(cfg)
    logger = setup_logging(cfg["paths"]["logs_dir"])

    if args.init and args.label:
        db_path = cfg["paths"]["db_path"]
        store = EventStore(db_path, logger, label=args.label)
        store.create_schema()
        session_id = str(uuid.uuid4())
        store.upsert_session(
            session_id=session_id,
            context="bootstrap",
            duration=0
        )
        store.close()

        # Update the config with the label
        cfg['session_label'] = args.label
        with open(args.config, "w") as f:
            yaml.safe_dump(cfg, f)

        logger.info("Initialized DB schema at %s", db_path)
    else:
        logger.info("No action. Use --init to create schema and --label to identify your db.")

if __name__ == "__main__":
    main()
