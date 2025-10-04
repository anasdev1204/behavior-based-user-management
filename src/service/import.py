from src.utils.config import load_config, ensure_dirs
from src.utils.logging import setup_logging
import requests, os

class Importer:
    def __init__(self, cfg):
        self.db_path = cfg['paths']['db_path']
        self.interim_dir = cfg['paths']['interim_dir']
        self.logger = setup_logging(cfg["paths"]["logs_dir"])
        self.base_url = cfg["base_url"]

    def import_from_server(self):
        """Download interim data from the server and store locally in self.interim_dir"""
        try:
            self.logger.info("Requesting interim data from server...")

            interim_files = os.listdir(os.path.join(os.getcwd(), self.interim_dir))


            resp = requests.post(
                f"{self.base_url}/api/import",
                json={
                    "existing_files": interim_files,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            download_urls: dict = data["download_urls"]

            self.logger.info(f"Got presigned URLs for {len(download_urls.keys())}, starting download...")

            for file_name,download_url in download_urls.items():
                download_resp = requests.get(download_url, stream=True)
                download_resp.raise_for_status()

                local_path = os.path.join(os.getcwd(), self.interim_dir, file_name)

                with open(local_path, "wb") as f:
                    for chunk in download_resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                self.logger.info(f"Downloaded {file_name} to {local_path}")

        except Exception as e:
            self.logger.error(f"Failed to import from server: {e}")
            raise


if __name__ == "__main__":
    cfg = load_config("config.yaml")
    ensure_dirs(cfg)

    importer = Importer(cfg)
    importer.import_from_server()
