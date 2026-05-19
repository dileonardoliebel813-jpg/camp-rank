from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.ingestion.sdk_clients import (  # noqa: E402
    JDUnionClient,
    PddOpenClient,
    RedBookAuthorizedClient,
    SMZDMOpenClient,
    TaobaoTopClient,
)


CLIENTS = {
    "jd": JDUnionClient,
    "smzdm": SMZDMOpenClient,
    "taobao": TaobaoTopClient,
    "pdd": PddOpenClient,
    "redbook": RedBookAuthorizedClient,
}


def main() -> int:
    successes = []
    skipped = []
    failed = {}
    for name, client_class in CLIENTS.items():
        client = client_class()
        if not client.enabled:
            skipped.append(name)
            continue
        try:
            result = client.smoke_test(keyword="帐篷", limit=3)
            successes.append({"source": name, "normalized_count": len(result.get("items", []))})
        except Exception as exc:  # noqa: BLE001 - smoke test reports platform failures cleanly
            failed[name] = str(exc)
    report = {
        "success_platforms": successes,
        "skipped_platforms": skipped,
        "failed_platforms": list(failed),
        "errors": failed,
    }
    if not successes and not failed:
        print("no official api enabled, skipped live smoke test.")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
