from __future__ import annotations

import json
import sys
from pathlib import Path

from app.core.config import get_settings


def _bool_mark(value: bool) -> str:
    return "OK" if value else "MISSING"


def _load_json_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def main() -> int:
    settings = get_settings()
    repo_root = Path(__file__).resolve().parents[3]
    mobile_google_services = repo_root / "mobile_app" / "android" / "app" / "google-services.json"

    print("=== ADR Push Setup Verification ===")
    print(f"repo_root: {repo_root}")
    print(f"android_google_services: {mobile_google_services}")

    project_id_set = bool((settings.fcm_project_id or "").strip())
    print(f"FCM_PROJECT_ID: {_bool_mark(project_id_set)}")

    credentials_path_value = (settings.fcm_credentials_path or "").strip()
    credentials_json_value = (settings.fcm_credentials_json or "").strip()
    credentials_ok = False
    credentials_project_id = None

    if credentials_path_value:
        credentials_path = Path(credentials_path_value).expanduser()
        payload = _load_json_file(credentials_path)
        credentials_ok = payload is not None
        credentials_project_id = (payload or {}).get("project_id")
        print(f"FCM_CREDENTIALS_PATH file: {_bool_mark(credentials_ok)} ({credentials_path})")
    elif credentials_json_value:
        if credentials_json_value.startswith("{"):
            try:
                parsed = json.loads(credentials_json_value)
                credentials_ok = isinstance(parsed, dict)
                if credentials_ok:
                    credentials_project_id = parsed.get("project_id")
            except json.JSONDecodeError:
                credentials_ok = False
            print(f"FCM_CREDENTIALS_JSON inline: {_bool_mark(credentials_ok)}")
        else:
            legacy_path = Path(credentials_json_value).expanduser()
            payload = _load_json_file(legacy_path)
            credentials_ok = payload is not None
            credentials_project_id = (payload or {}).get("project_id")
            print(f"FCM_CREDENTIALS_JSON path: {_bool_mark(credentials_ok)} ({legacy_path})")
    else:
        print("FCM credentials: MISSING")

    google_payload = _load_json_file(mobile_google_services)
    google_ok = google_payload is not None
    print(f"google-services.json: {_bool_mark(google_ok)}")

    google_project_id = None
    if google_ok:
        project_info = google_payload.get("project_info", {})
        if isinstance(project_info, dict):
            google_project_id = project_info.get("project_id")
        clients = google_payload.get("client", [])
        if isinstance(clients, list) and clients:
            try:
                package_name = clients[0]["client_info"]["android_client_info"]["package_name"]
            except Exception:
                package_name = None
            if package_name:
                print(f"android package_name: {package_name}")

    if credentials_project_id:
        print(f"credentials project_id: {credentials_project_id}")
    if google_project_id:
        print(f"google-services project_id: {google_project_id}")

    if (
        project_id_set
        and credentials_project_id
        and settings.fcm_project_id != credentials_project_id
    ):
        print("WARN: FCM_PROJECT_ID does not match service-account project_id")
    if project_id_set and google_project_id and settings.fcm_project_id != google_project_id:
        print("WARN: FCM_PROJECT_ID does not match google-services project_id")

    ready = project_id_set and credentials_ok and google_ok
    print(f"push_ready: {_bool_mark(ready)}")

    if not ready:
        print("")
        print("Action required:")
        print("1) set FCM_PROJECT_ID in backend/.env")
        print("2) set FCM_CREDENTIALS_PATH to your Firebase service-account JSON file path")
        print("3) place google-services.json at mobile_app/android/app/google-services.json")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
