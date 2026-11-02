"""English GK Drive-stock publisher.

Publishes the next cleared video straight from the owner's private Drive stock
(his approved plan, 2026-10-31): read-only keyless service account, one video
per due IST slot, with each video's own SEO from its ZIP manifest. Fails
loudly; reserves durable state before any external upload.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IST = timezone(timedelta(hours=5, minutes=30))
ZIP_NAME = re.compile(r"^unused([A-Z]\d+)_\d+\.zip$")
QID = re.compile(r"^q(\d{4})$")
DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive.readonly"]


def load(p):
    return json.loads(Path(p).read_text())


def save(p, x):
    Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2) + "\n")


def persist(state_dir, state, config, note):
    save(state_dir / config["state_file"], state)
    for args in (
        ("add", config["state_file"]),
        ("commit", "-m", note),
        ("push", "origin", "HEAD:" + config["state_branch"]),
    ):
        subprocess.run(["git", "-C", str(state_dir), *args], check=True, stdout=subprocess.DEVNULL)


def parse_manifest_name(name):
    m = MANIFEST_NAME.match(name)
    return m.group(1) if m else None


def select_slot(now, config, state):
    local = now.astimezone(IST)
    today = local.date().isoformat()
    if today <= config.get("studio_slots_until", ""):
        return None  # owner-scheduled Studio uploads hold all slots until that date
    for name, clock in config["slots"].items():
        h, m = map(int, clock.split(":"))
        opening = local.replace(hour=h, minute=m, second=0, microsecond=0)
        lag = (local - opening).total_seconds()
        key = f"{today}:{name}"
        if 0 <= lag < config["window_minutes"] * 60 and state.get("slots", {}).get(key, {}).get("status") != "published":
            return {"key": key, "slot": name, "opens_at": opening.isoformat(), "drift_seconds": round(lag)}
    return None


def select_run_slot(now, config, state, mode):
    if mode == "scheduled":
        return select_slot(now, config, state)
    local = now.astimezone(IST)
    return {"key": f"manual:{local.date()}", "slot": "manual", "opens_at": now.isoformat(), "drift_seconds": 0}


def dispatch_mode(event, mode=None):
    if event != "workflow_dispatch":
        return "scheduled"
    mode = mode or "manual"
    if mode not in ("manual", "scheduled"):
        raise ValueError("Invalid dispatch mode")
    return mode


def validate_video_entry(v, config):
    qid = v.get("question_id", "")
    m = QID.match(qid)
    if not m:
        raise ValueError("Invalid question_id in stock manifest")
    if int(m.group(1)) <= int(config.get("skip_qid_range_end", 0)):
        raise ValueError("already-published bank range")
    title = v.get("title", "")
    if not title.strip() or len(title) > 100:
        raise ValueError("Invalid title length")
    if len(v.get("description", "")) > 5000:
        raise ValueError("Description too long")
    if not (0 < float(v.get("duration", 0)) <= 35.0):
        raise ValueError("Stock video exceeds the 35 s format cap")
    if not v.get("file") or not v.get("sha256"):
        raise ValueError("Manifest missing file or sha256")
    return qid


def drive_client():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    raw = os.environ.get("GDRIVE_SA_KEY_JSON", "").strip()
    if not raw:
        raise RuntimeError("Missing repository secret: GDRIVE_SA_KEY_JSON")
    creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=DRIVE_SCOPE)
    return build("drive", "v3", credentials=creds)


def list_stock(drive, folder_id):
    items, token = [], None
    while True:
        resp = (
            drive.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false and name contains 'unused'",
                fields="nextPageToken, files(id,name,md5Checksum,size)",
                pageSize=1000,
                pageToken=token,
                orderBy="name",
            )
            .execute()
        )
        items.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            return items


def download_zip(drive, file_id, dest):
    from googleapiclient.http import MediaIoBaseDownload

    request = drive.files().get_media(fileId=file_id)
    with open(dest, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def recent_titles(youtube, scan):
    channels = youtube.channels().list(part="contentDetails", mine=True).execute().get("items", [])
    if len(channels) != 1:
        raise RuntimeError("OAuth identity mismatch while reading uploads playlist")
    uploads = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    titles, token = set(), None
    while len(titles) < scan:
        resp = youtube.playlistItems().list(part="snippet", playlistId=uploads, maxResults=50, pageToken=token).execute()
        for item in resp.get("items", []):
            titles.add(item["snippet"].get("title", ""))
        token = resp.get("nextPageToken")
        if not token or len(resp.get("items", [])) == 0:
            break
    return titles


def manifest_candidates(stock, config):
    published_range_end = int(config.get("skip_qid_range_end", 0))
    out = []
    for item in sorted(stock, key=lambda f: f["name"]):
        qid = parse_manifest_name(item["name"])
        if qid and int(qid[1:]) > published_range_end:
            out.append((qid, item))
    return out


def main():
    config = load(ROOT / "data/stock_config.json")
    sd = Path(os.environ["PUBLICATION_STATE_DIR"])
    state_path = sd / config["state_file"]
    state = load(state_path) if state_path.is_file() else {"slots": {}, "published_ids": [], "checks": [], "skipped_external": []}
    now = datetime.now(timezone.utc)
    mode = dispatch_mode(os.getenv("GITHUB_EVENT_NAME"), os.getenv("DISPATCH_MODE"))
    slot = select_run_slot(now, config, state, mode)
    state.setdefault("checks", []).append(
        {"at": now.isoformat(), "run_id": os.getenv("GITHUB_RUN_ID"), "event": os.getenv("GITHUB_EVENT_NAME"), "slot": slot, "mode": mode}
    )
    state["checks"] = state["checks"][-500:]
    if not slot:
        persist(sd, state, config, "Record Hindi stock slot check")
        print("No active IST slot")
        return
    previous = state.setdefault("slots", {}).get(slot["key"], {})
    if previous.get("status") in ("pending", "ambiguous"):
        persist(sd, state, config, "Record blocked pending Hindi stock publication")
        raise RuntimeError("Reconcile pending receipt before retry")

    drive = drive_client()
    stock = list_stock(drive, config["drive_root_folder_id"])
    candidates = manifest_candidates(stock, config)
    if not candidates:
        persist(sd, state, config, "Record Hindi stock slot with no stock manifests")
        print("No stock manifests")
        return

    sys.path.insert(0, str(ROOT / "scripts"))
    from upload_youtube import get_youtube_client, upload_short

    for name in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        if not os.getenv(name):
            raise RuntimeError("Missing repository secret: " + name)
    youtube = get_youtube_client()
    items = youtube.channels().list(part="id", mine=True).execute().get("items", [])
    if [c.get("id") for c in items] != [config["channel_id"]]:
        raise RuntimeError("OAuth identity mismatch: refusing to publish to a non-Hindi channel")
    known_titles = recent_titles(youtube, int(config.get("recent_upload_scan", 100)))

    published = set(state.get("published_ids", []))
    published.update(x.get("question_id") for x in state.get("slots", {}).values() if x.get("status") in ("pending", "ambiguous", "published"))

    work = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "hi-stock"
    work.mkdir(parents=True, exist_ok=True)
    chosen = None
    for qid, item in candidates:
        if qid in published:
            continue
        doc = json.loads(download_file(drive, item["id"]).decode("utf-8"))
        seo = doc.get("seo", {})
        meta = doc.get("manifest", {})
        if meta.get("published") is True:
            state.setdefault("skipped_external", []).append({"question_id": qid, "reason": "manifest marked published", "at": now.isoformat()})
            continue
        title = seo.get("title", "")
        if not title.strip() or len(title) > 100:
            state.setdefault("skipped_external", []).append({"question_id": qid, "reason": "invalid title", "at": now.isoformat()})
            continue
        if title in known_titles:
            state.setdefault("skipped_external", []).append({"question_id": qid, "reason": "title already on channel", "at": now.isoformat()})
            continue
        video_item = find_video(drive, item["batch_folder_id"], qid)
        if not video_item:
            state.setdefault("skipped_external", []).append({"question_id": qid, "reason": "mp4 missing", "at": now.isoformat()})
            continue
        payload = download_file(drive, video_item["id"])
        if len(payload) < 100000:
            raise ValueError(f"Stock video suspiciously small for {qid}")
        chosen = (qid, seo, payload)
        break
    if not chosen:
        persist(sd, state, config, "Record Hindi stock slot with all candidates skipped")
        print("No eligible stock candidate")
        return

    qid, seo, payload = chosen
    video_path = work / (qid + ".mp4")
    video_path.write_bytes(payload)
    state["slots"][slot["key"]] = dict(slot, status="pending", question_id=qid, run_id=os.getenv("GITHUB_RUN_ID"))
    persist(sd, state, config, "Reserve exact Hindi stock asset before external upload")
    try:
        receipt = upload_short(str(video_path), seo["title"], seo.get("description", ""), tags=seo.get("tags"))
    except Exception:
        state["slots"][slot["key"]]["status"] = "ambiguous"
        persist(sd, state, config, "Hold uncertain Hindi stock upload for reconciliation")
        raise
    destinations = {"youtube": receipt}
    state["slots"][slot["key"]].update(status="published", youtube_id=receipt, destinations=destinations, published_at=datetime.now(timezone.utc).isoformat())
    state.setdefault("published_ids", []).append(qid)
    persist(sd, state, config, "Record confirmed Hindi stock YouTube receipt")
    if not config.get("instagram_enabled", False):
        print("Instagram disabled this run; YouTube only.")
    print(json.dumps({"question_id": qid, "youtube_id": receipt, "slot": slot["key"], "drift_seconds": slot["drift_seconds"]}))


if __name__ == "__main__":
    main()
