import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")


def _default_database_url() -> str:
    db_path = BACKEND_ROOT / "camp_rank.db"
    return f"sqlite:///{db_path.as_posix()}"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    project_name: str = "CampRank"
    database_url: str = _default_database_url()
    sample_data_enabled: bool = False
    smzdm_api_enabled: bool = False
    smzdm_api_key: str = ""
    smzdm_base_url: str = ""
    smzdm_search_path: str = ""
    smzdm_detail_path: str = ""
    jd_api_enabled: bool = False
    jd_app_key: str = ""
    jd_app_secret: str = ""
    jd_base_url: str = ""
    jd_api_method_search: str = ""
    jd_api_method_detail: str = ""
    taobao_api_enabled: bool = False
    taobao_app_key: str = ""
    taobao_app_secret: str = ""
    taobao_base_url: str = ""
    taobao_adzone_id: str = ""
    taobao_search_method: str = "taobao.tbk.dg.material.optional"
    pdd_api_enabled: bool = False
    pdd_client_id: str = ""
    pdd_client_secret: str = ""
    pdd_base_url: str = ""
    pdd_search_method: str = "pdd.ddk.goods.search"
    pdd_detail_method: str = "pdd.ddk.goods.detail"
    redbook_api_enabled: bool = False
    redbook_app_id: str = ""
    redbook_app_secret: str = ""
    redbook_base_url: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", _default_database_url()),
            sample_data_enabled=_env_bool("SAMPLE_DATA_ENABLED"),
            smzdm_api_enabled=_env_bool("SMZDM_API_ENABLED"),
            smzdm_api_key=os.getenv("SMZDM_API_KEY", ""),
            smzdm_base_url=os.getenv("SMZDM_BASE_URL", ""),
            smzdm_search_path=os.getenv("SMZDM_SEARCH_PATH", ""),
            smzdm_detail_path=os.getenv("SMZDM_DETAIL_PATH", ""),
            jd_api_enabled=_env_bool("JD_API_ENABLED"),
            jd_app_key=os.getenv("JD_APP_KEY", ""),
            jd_app_secret=os.getenv("JD_APP_SECRET", ""),
            jd_base_url=os.getenv("JD_BASE_URL", ""),
            jd_api_method_search=os.getenv("JD_API_METHOD_SEARCH") or os.getenv("JD_API_METHOD", ""),
            jd_api_method_detail=os.getenv("JD_API_METHOD_DETAIL", ""),
            taobao_api_enabled=_env_bool("TAOBAO_API_ENABLED"),
            taobao_app_key=os.getenv("TAOBAO_APP_KEY", ""),
            taobao_app_secret=os.getenv("TAOBAO_APP_SECRET", ""),
            taobao_base_url=os.getenv("TAOBAO_BASE_URL", ""),
            taobao_adzone_id=os.getenv("TAOBAO_ADZONE_ID", ""),
            taobao_search_method=os.getenv("TAOBAO_SEARCH_METHOD", "taobao.tbk.dg.material.optional"),
            pdd_api_enabled=_env_bool("PDD_API_ENABLED"),
            pdd_client_id=os.getenv("PDD_CLIENT_ID", ""),
            pdd_client_secret=os.getenv("PDD_CLIENT_SECRET", ""),
            pdd_base_url=os.getenv("PDD_BASE_URL", ""),
            pdd_search_method=os.getenv("PDD_SEARCH_METHOD", "pdd.ddk.goods.search"),
            pdd_detail_method=os.getenv("PDD_DETAIL_METHOD", "pdd.ddk.goods.detail"),
            redbook_api_enabled=_env_bool("REDBOOK_API_ENABLED"),
            redbook_app_id=os.getenv("REDBOOK_APP_ID", ""),
            redbook_app_secret=os.getenv("REDBOOK_APP_SECRET", ""),
            redbook_base_url=os.getenv("REDBOOK_BASE_URL", ""),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            deepseek_timeout_seconds=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "20")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
