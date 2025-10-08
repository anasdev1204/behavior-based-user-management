from src.utils.config import load_config, ensure_dirs
from src.utils.logging import setup_logging
import sqlite3, pathlib, hashlib, csv, requests, os
import pandas as pd

class Exporter:
    def __init__(self, cfg):
        self.db_path = cfg['paths']['db_path']
        self.output_path = cfg['paths']['raw_dir']
        self.label = cfg["session_label"]
        self.logger = setup_logging(cfg["paths"]["logs_dir"])
        self.base_url = cfg["base_url"]

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
        output_files = os.listdir(self.output_path)
        csv_output_path = pathlib.Path(self.output_path) / "output.csv"
        i = 1
        while csv_output_path.name in output_files:
            csv_output_path = pathlib.Path(self.output_path) / f"output_{i}.csv"
            i += 1

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

                df = pd.DataFrame()
                if len(output_files) > 0:
                    for o_f in output_files:
                        if o_f.endswith(".csv"):
                            df = pd.concat([df, pd.read_csv(
                                pathlib.Path(self.output_path) / o_f
                            )], ignore_index=True)

                # Build sessions dict from the first table
                try:
                    sessions_table = next(iter(table_data))
                    sessions = {}
                    for row in table_data[sessions_table]["rows"]:
                        session_id = row["session_id"]
                        if (not "session_id" in df.columns) or (session_id not in df["session_id"].tolist()):
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
                            if session_id not in sessions.keys():
                                continue

                            sessions[session_id].update({k: v for k, v in r.items() if k != "id"})
                        self.logger.info(f"Merged {len(rows)} rows from table `{table_name}` into sessions")
                    except Exception as e:
                        self.logger.error(f"Failed to merge table `{table_name}`: {e}")

                row_data = [v for v in sessions.items()]

                if len(row_data) > 0:
                    # Write to CSV
                    try:
                        with csv_output_path.open("w", newline="", encoding="utf-8") as f:
                            all_columns = [col for col in all_columns if col != "id"]

                            writer = csv.DictWriter(f, fieldnames=all_columns)
                            writer.writeheader()
                            for session_id, session in row_data:
                                row_to_write = {col: session.get(col, None) for col in all_columns}
                                writer.writerow(row_to_write)
                        self.logger.info(f"Wrote to {csv_output_path}")
                        self.logger.info(f"CSV file has {len(row_data)} rows and {len(all_columns)} columns")
                    except Exception as e:
                        self.logger.error(f"Failed to write CSV: {e}")
                        raise
                else:
                    self.logger.warning("No new rows to export")

                return csv_output_path, len(row_data) > 0

        except Exception as e:
            self.logger.exception(f"Export failed: {e}")
            raise

    @staticmethod
    def calculate_checksum(file_path: pathlib.Path) -> str:
        """Calculate SHA256 checksum of the file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def upload_to_server(self, csv_output_path: pathlib.Path):
        """Upload the output file to server"""
        file_size = csv_output_path.stat().st_size
        checksum = self.calculate_checksum(csv_output_path)

        self.logger.info(f"Uploading {file_size} bytes to server")

        presign_resp = requests.post(
            f"{self.base_url}/api/presign",
            json={
                "file_name": csv_output_path.name,
                "size": file_size,
                "checksum": checksum,
                "label": self.label
            },
        )
        presign_resp.raise_for_status()
        data = presign_resp.json()

        upload_url = data["upload_url"]
        token = data["token"]

        with open(csv_output_path, "rb") as f:
            upload_resp = requests.put(
                upload_url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "text/csv"},
                data=f,
            )
        upload_resp.raise_for_status()

        self.logger.info(f"Uploaded to server")


if __name__ == "__main__":
    cfg = load_config("config.yaml")
    ensure_dirs(cfg)

    exporter = Exporter(cfg)
    csv_output_path, is_new_data = exporter.export_to_csv()
    if is_new_data:
        exporter.upload_to_server(csv_output_path)
