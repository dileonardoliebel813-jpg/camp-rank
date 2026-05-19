from app.ingestion.import_report import ImportReport
from app.ingestion.import_service import import_from_csv_folder
from app.ingestion.platform_adapters.base_adapter import BasePlatformAdapter


class CsvAdapter(BasePlatformAdapter):
    source_name = "manual_csv"

    def __init__(self, folder_path: str | None = None):
        self.folder_path = folder_path

    def fetch_raw_data(self, keyword: str = "", limit: int = 20) -> dict:
        return {"folder_path": self.folder_path}

    def normalize(self, raw_data: dict) -> dict:
        return raw_data

    def import_to_db(self, db, normalized_data: dict) -> ImportReport:
        return import_from_csv_folder(db, normalized_data["folder_path"], source_name=self.source_name)

