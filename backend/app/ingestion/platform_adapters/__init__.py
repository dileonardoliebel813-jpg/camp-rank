from app.ingestion.platform_adapters.jd_adapter import JDAdapter
from app.ingestion.platform_adapters.json_adapter import JsonAdapter
from app.ingestion.platform_adapters.csv_adapter import CsvAdapter
from app.ingestion.platform_adapters.pdd_adapter import PddAdapter
from app.ingestion.platform_adapters.redbook_adapter import RedBookAdapter
from app.ingestion.platform_adapters.smzdm_adapter import SMZDMAdapter
from app.ingestion.platform_adapters.taobao_adapter import TaobaoAdapter

__all__ = [
    "CsvAdapter",
    "JDAdapter",
    "JsonAdapter",
    "PddAdapter",
    "RedBookAdapter",
    "SMZDMAdapter",
    "TaobaoAdapter",
]

