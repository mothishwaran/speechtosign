"""Fetch ISL dictionary clips from Google Drive on demand, then cache them.

data/drive_manifest.csv (built by tools/build_manifest.py) lists ~3,000
phrases that exist on the ISLRTC Drive but not on this machine. When a
transcript needs one, the server downloads that single file into
data/_source/isl_dictionary/ - the same place a manual download would put
it - so every later request plays it instantly from disk.

Runs on the server only: the Google API key never reaches the browser.
A fetched file is checked before use: longer than 30 s means it is a
lecture about the word, not the sign, and it is rejected (and remembered,
so it is never fetched again); codecs browsers cannot play are transcoded.
"""
import csv
import os
import sys
import threading
import time
import urllib.error
import urllib.request

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = "data/_source/isl_dictionary"
DERIVED_DIR = "data/_derived/h264"
REJECTED_CSV = os.path.join(_REPO_ROOT, "data", "_derived", "drive_rejected.csv")
API = "https://www.googleapis.com/drive/v3/files"
MAX_SECONDS = 30.0
BROWSER_SAFE = {"h264"}

_lock = threading.Lock()
_rejected: set | None = None


def api_key() -> str | None:
    key = os.environ.get("GOOGLE_API_KEY")
    if not key and sys.platform == "win32":
        import winreg   # `setx` values only reach newly started programs
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = winreg.QueryValueEx(k, "GOOGLE_API_KEY")[0]
        except OSError:
            key = None
    return key or None


def rejected() -> set:
    """Drive files already found unusable (too long / undecodable)."""
    global _rejected
    if _rejected is None:
        _rejected = set()
        if os.path.exists(REJECTED_CSV):
            with open(REJECTED_CSV, newline="", encoding="utf-8") as f:
                _rejected = {r["rel"] for r in csv.DictReader(f)}
    return _rejected


def _reject(rel: str, reason: str) -> None:
    with _lock:
        rejected().add(rel)
        new = not os.path.exists(REJECTED_CSV)
        os.makedirs(os.path.dirname(REJECTED_CSV), exist_ok=True)
        with open(REJECTED_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["rel", "reason"])
            w.writerow([rel, reason])


def local_path(rel: str) -> str:
    return f"{SOURCE_DIR}/{rel}"


def playable_path(rel: str) -> str | None:
    """Repo-relative path the browser can play, if the clip is already cached."""
    derived = f"{DERIVED_DIR}/{os.path.splitext(rel)[0]}.mp4"
    if os.path.exists(os.path.join(_REPO_ROOT, derived)):
        return derived
    if os.path.exists(os.path.join(_REPO_ROOT, local_path(rel))):
        return local_path(rel)
    return None


_file_locks: dict = {}


def fetch(drive_id: str, rel: str, timeout: float = 30.0) -> tuple[str | None, str]:
    """Download + validate one clip. Returns (playable repo-relative path, status).

    Serialised per file, so two requests needing the same new sign never
    write the same .part file at once; the second finds it cached.
    """
    with _lock:
        file_lock = _file_locks.setdefault(rel, threading.Lock())
    with file_lock:
        return _fetch(drive_id, rel, timeout)


def _fetch(drive_id: str, rel: str, timeout: float) -> tuple[str | None, str]:
    if rel in rejected():
        return None, "rejected earlier"
    cached = playable_path(rel)
    if cached:
        return cached, "cached"
    key = api_key()
    if not key:
        return None, "no GOOGLE_API_KEY"

    dst = os.path.join(_REPO_ROOT, SOURCE_DIR, *rel.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = f"{API}/{drive_id}?alt=media&key={key}"
    err = "unknown error"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp, open(dst + ".part", "wb") as f:
                while chunk := resp.read(1 << 20):
                    f.write(chunk)
            os.replace(dst + ".part", dst)
            break
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.code == 403 and b"downloadQuotaExceeded" in body:
                return None, "Drive download quota exceeded (try tomorrow)"
            err = f"HTTP {e.code}"
        except OSError as e:
            err = str(e)[:80]
        time.sleep(1 + attempt)
    else:
        return None, f"download failed: {err}"

    import av
    try:
        c = av.open(dst)
        codec = c.streams.video[0].codec_context.name
        duration = float(c.duration / 1e6) if c.duration else 0.0
        c.close()
    except Exception as e:  # truncated or not a video
        os.remove(dst)
        _reject(rel, f"undecodable: {e!r}"[:120])
        return None, "downloaded file is not a playable video"
    if duration > MAX_SECONDS:
        _reject(rel, f"{duration:.0f}s long")
        return None, f"clip is {duration:.0f}s (a lecture, not a sign) - skipped"
    if codec not in BROWSER_SAFE:
        sys.path.insert(0, _REPO_ROOT)
        from tools.build_manifest import transcode_h264
        out = f"{DERIVED_DIR}/{os.path.splitext(rel)[0]}.mp4"
        transcode_h264(dst, os.path.join(_REPO_ROOT, out))
        return out, f"downloaded + transcoded from {codec}"
    return local_path(rel), "downloaded"
