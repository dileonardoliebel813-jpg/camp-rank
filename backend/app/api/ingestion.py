from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.import_report import ImportReport
from app.ingestion.fetch_service import fetch_and_import, get_last_fetch_report
from app.ingestion.import_service import import_from_json
from app.ingestion.jd_comment_importer import import_jd_comments_json
from app.ingestion.jd_public_comments import JDPublicCommentFetcher
from app.ingestion.platform_mapping import get_platform_mapping_summary
from app.ingestion.report_store import get_last_quality_report


router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])
LAST_IMPORT_REPORT: ImportReport | None = None


class ImportJsonRequest(BaseModel):
    path: str
    source_name: str = "manual_json"


class FetchRealRequest(BaseModel):
    source: str
    keyword: str
    limit: int = 20
    live: bool = False
    input_path: str | None = None
    dry_run: bool = False
    save_json: bool = False


class FetchOfficialRequest(BaseModel):
    source: str
    keyword: str
    limit: int = 5
    live: bool = True
    dry_run: bool = True
    save_json: bool = False


class FetchJDCommentsRequest(BaseModel):
    sku_id: str
    max_pages: int = 3
    page_size: int = 10
    save_only: bool = True


class ImportJDCommentsRequest(BaseModel):
    path: str


def _safe_real_sample_path(path_text: str) -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    project_root = backend_root.parent
    allowed_root = (backend_root / "data" / "real_samples").resolve()
    raw = Path(path_text)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([project_root / raw, backend_root / raw])
    for candidate in candidates:
        resolved = candidate.resolve()
        if allowed_root == resolved or allowed_root in resolved.parents:
            return resolved
    raise HTTPException(status_code=400, detail="Only files under backend/data/real_samples are allowed.")


@router.post("/import-json")
def import_json(request: ImportJsonRequest, db: Session = Depends(get_db)):
    global LAST_IMPORT_REPORT
    path = _safe_real_sample_path(request.path)
    if not path.exists() or path.suffix.lower() != ".json":
        raise HTTPException(status_code=404, detail="JSON sample file not found.")
    LAST_IMPORT_REPORT = import_from_json(db, str(path), source_name=request.source_name)
    return LAST_IMPORT_REPORT


@router.get("/import-status")
def import_status():
    if LAST_IMPORT_REPORT is None:
        return {"status": "empty", "last_import_report": None}
    return {"status": "ok", "last_import_report": LAST_IMPORT_REPORT}


@router.post("/fetch-real")
def fetch_real(request: FetchRealRequest, db: Session = Depends(get_db)):
    input_path = request.input_path
    if not request.live:
        if not input_path:
            return fetch_and_import(
                db,
                source=request.source,
                keyword=request.keyword,
                limit=request.limit,
                live=False,
                input_path=None,
            )
        path = _safe_real_sample_path(input_path)
        if not path.exists() or path.suffix.lower() != ".json":
            raise HTTPException(status_code=404, detail="JSON sample file not found.")
        input_path = str(path)
    return fetch_and_import(
        db,
        source=request.source,
        keyword=request.keyword,
        limit=request.limit,
        live=request.live,
        input_path=input_path,
        dry_run=request.dry_run,
        save_json=request.save_json,
    )


@router.post("/fetch-official")
def fetch_official(request: FetchOfficialRequest, db: Session = Depends(get_db)):
    return fetch_and_import(
        db,
        source=request.source,
        keyword=request.keyword,
        limit=request.limit,
        live=request.live,
        dry_run=request.dry_run,
        save_json=request.save_json,
    )


@router.post("/jd-comments/fetch")
def fetch_jd_comments(request: FetchJDCommentsRequest, db: Session = Depends(get_db)):
    fetcher = JDPublicCommentFetcher()
    result = fetcher.fetch_comments(
        sku_id=request.sku_id,
        max_pages=request.max_pages,
        page_size=request.page_size,
        delay_seconds=2.0,
    )
    saved_json_path = fetcher.save_comments_json(request.sku_id, result["comments"])
    response = {
        "fetched_count": len(result["comments"]),
        "saved_json_path": saved_json_path,
        "warnings": result["warnings"],
        "errors": result["errors"],
    }
    if not request.save_only and not result["errors"]:
        import_report = import_jd_comments_json(db, saved_json_path)
        response["import_report"] = import_report
        response["warnings"].extend(import_report.warnings)
        response["errors"].extend(import_report.errors)
    return response


@router.post("/jd-comments/import")
def import_jd_comments(request: ImportJDCommentsRequest, db: Session = Depends(get_db)):
    path = _safe_real_sample_path(request.path)
    if not path.exists() or path.suffix.lower() != ".json":
        raise HTTPException(status_code=404, detail="JD comments JSON file not found.")
    return import_jd_comments_json(db, str(path))


@router.get("/fetch-status")
def fetch_status():
    return get_last_fetch_report()


@router.get("/platform-mapping")
def platform_mapping():
    return {"platforms": get_platform_mapping_summary()}


@router.get("/quality-report")
def quality_report():
    return get_last_quality_report()
