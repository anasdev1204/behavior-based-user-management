from src.utils.config import load_config, ensure_dirs
from src.utils.logging import setup_logging
import sqlite3, pathlib, csv

class Exporter:

    def __init__(self, cfg):
        self.db_path = cfg['paths']['db_path']
        self.output_path = cfg['paths']['raw_dir']
        self.logger = setup_logging(cfg["paths"]["logs_dir"])

    def _get_db(self):
        """Connect to SQLite DB and return connection"""
        try:
            conn = sqlite3.connect(self.db_path)
            self.logger.info(f"Connected to database at {self.db_path}")
            return conn
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise

    def export_to_csv(self):
        """Export all tables into one CSV joined on session_id"""
        try:
            with self._get_db() as conn:
                cursor = conn.cursor()

                # Get tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [name for (name,) in cursor.fetchall() if not name.startswith("sqlite_")]
                if not tables:
                    self.logger.warning("No tables found in database")
                    return None

                self.logger.info(f"Found tables: {tables}")

                all_columns = ["session_id"]
                table_data = {}

                for table in tables:
                    try:
                        cursor.execute(f"PRAGMA table_info({table})")
                        col_info = cursor.fetchall()
                        col_names = [col[1] for col in col_info]

                        if "session_id" not in col_names:
                            self.logger.warning(f"Skipping table `{table}` (no session_id column)")
                            continue

                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        self.logger.info(f"Table `{table}` has {len(rows)} rows")

                        table_data[table] = {
                            "columns": col_names,
                            "rows": [dict(zip(col_names, row)) for row in rows]
                        }
                        all_columns += col_names
                    except Exception as e:
                        self.logger.error(f"Failed to load table `{table}`: {e}")

                all_columns = list(set(all_columns))
                all_columns = (
                    ["session_id"] +
                    [col for col in all_columns if col not in ("session_id", "label")] +
                    ["label"]
                ) # Sort the tables so that session_id is always first and label always last

                if not table_data:
                    self.logger.warning("No tables with session_id column found")
                    return None

                # Build sessions dict from the first table
                try:
                    sessions_table = next(iter(table_data))
                    sessions = {}
                    for row in table_data[sessions_table]["rows"]:
                        sessions[row["session_id"]] = row
                    del table_data[sessions_table]
                    self.logger.info(f"Sessions initialized from table `{sessions_table}` ({len(sessions)} rows)")
                except Exception as e:
                    self.logger.error(f"Failed to initialize sessions from first table: {e}")
                    raise

                # Merge other tables into sessions
                for table_name, tdata in table_data.items():
                    try:
                        rows = tdata["rows"]
                        for r in rows:
                            session_id = r["session_id"]
                            if session_id not in sessions:
                                sessions[session_id] = {}
                            sessions[session_id].update({k: v for k, v in r.items() if k != "id"})
                        self.logger.info(f"Merged {len(rows)} rows from table `{table_name}` into sessions")
                    except Exception as e:
                        self.logger.error(f"Failed to merge table `{table_name}`: {e}")

                row_data = [v for v in sessions.items()]

                # Write to CSV
                try:
                    output_path = pathlib.Path(self.output_path) / "output.csv"
                    with output_path.open("w", newline="", encoding="utf-8") as f:
                        all_columns = [col for col in all_columns if col != "id"]
                        writer = csv.DictWriter(f, fieldnames=all_columns)
                        writer.writeheader()
                        for session_id, session in row_data:
                            row_to_write = {col: session.get(col, None) for col in all_columns}
                            writer.writerow(row_to_write)
                    self.logger.info(f"Wrote to {output_path}")
                    self.logger.info(f"CSV file has {len(row_data)} rows and {len(all_columns)} columns")
                except Exception as e:
                    self.logger.error(f"Failed to write CSV: {e}")
                    raise

                return output_path

        except Exception as e:
            self.logger.exception(f"Export failed: {e}")
            raise

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    ensure_dirs(cfg)

    exporter = Exporter(cfg)
    exporter.export_to_csv()
