"""Fetch missing ISL Dictionary clips straight from the public Google Drive folder.

The Drive download arrives as ~2 GB zip parts, and a partial download leaves
words missing (e.g. "boy"). This lists the whole Drive folder through the
Drive API (names and ids only - no video), compares it with
data/_source/isl_dictionary/, and downloads just the clips you ask for into
the same relative path. tools/build_manifest.py then picks them up unchanged.

Needs a Google API key with the Drive API enabled, in GOOGLE_API_KEY (never
committed). Free; no billing account.

Usage:
  python tools/drive_sync.py index                    # list Drive -> data/_derived/drive_index.csv
  python tools/drive_sync.py missing [--words a,b]    # what Drive has that we don't
  python tools/drive_sync.py download --words boy,want,tell
  python tools/drive_sync.py download --words-file eval/wanted_words.txt
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from tools.build_manifest import SOURCE_DIR, VIDEO_EXTS, parse_name  # noqa: E402

ROOT_FOLDER_ID = "1U-Pr4r1-cupgNOOq9NH_uTsQnPSVEKco"
INDEX_CSV = "data/_derived/drive_index.csv"
API = "https://www.googleapis.com/drive/v3/files"


def api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY")
    if not key and sys.platform == "win32":
        # `setx` only reaches newly started programs; read the stored value directly.
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = winreg.QueryValueEx(k, "GOOGLE_API_KEY")[0]
        except OSError:
            pass
    if not key:
        sys.exit("GOOGLE_API_KEY not set - see README (Drive sync).")
    return key


def _get(params: dict, key: str, retries: int = 5) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "key": key})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 500, 503) and attempt < retries - 1:
                time.sleep(2 ** attempt)        # rate limit / transient: back off
                continue
            sys.exit(f"Drive API error {e.code}: {e.read().decode()[:300]}")
    raise RuntimeError("unreachable")


def list_folder(folder_id: str, key: str):
    token = None
    while True:
        params = {"q": f"'{folder_id}' in parents and trashed=false", "pageSize": 1000,
                  "fields": "nextPageToken,files(id,name,mimeType,size)",
                  "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
        if token:
            params["pageToken"] = token
        d = _get(params, key)
        yield from d.get("files", [])
        token = d.get("nextPageToken")
        if not token:
            return


def cmd_index(_args):
    key = api_key()
    rows, stack = [], [(ROOT_FOLDER_ID, "")]
    while stack:
        fid, prefix = stack.pop()
        for f in list_folder(fid, key):
            # Drive names can carry stray spaces ("NCERT 156 new "); local
            # extraction trims them, so compare on the trimmed form.
            name = f["name"].strip()
            rel = f"{prefix}{name}"
            if f["mimeType"] == "application/vnd.google-apps.folder":
                stack.append((f["id"], rel + "/"))
            elif os.path.splitext(name)[1].lower() in VIDEO_EXTS:
                rows.append({"rel": rel, "id": f["id"], "size": f.get("size", "")})
        print(f"  indexed {len(rows)} videos...", end="\r", flush=True)
    os.makedirs(os.path.dirname(INDEX_CSV), exist_ok=True)
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rel", "id", "size"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["rel"]))
    print(f"\nDrive has {len(rows)} videos -> {INDEX_CSV}")


def load_index():
    if not os.path.exists(INDEX_CSV):
        sys.exit("run `python tools/drive_sync.py index` first")
    with open(INDEX_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def local_rels() -> set:
    out = set()
    for dp, _, fns in os.walk(SOURCE_DIR):
        for fn in fns:
            out.add(os.path.relpath(os.path.join(dp, fn), SOURCE_DIR).replace(os.sep, "/").strip())
    return out


def missing_rows(words=None):
    have = local_rels()
    rows = [r for r in load_index() if r["rel"] not in have]
    if words:
        # One clip per wanted phrase, ranked like build_manifest (no
        # explanation videos, plain name over synonym list, unqualified,
        # sign 1 before sign 2) with file size standing in for duration -
        # the duration is unknown until the file is downloaded.
        wanted = {w.strip().lower() for w in words if w.strip()}
        best = {}
        for r in rows:
            for c in parse_name(r["rel"])[0]:
                if c["phrase"] not in wanted or c["explanation"]:
                    continue
                key = (c["from_synonym"], bool(c["qualifiers"]), c["variant"], int(r["size"] or 0))
                if c["phrase"] not in best or key < best[c["phrase"]][0]:
                    best[c["phrase"]] = (key, r)
        uniq = {r["rel"]: r for _, r in best.values()}
        rows = sorted(uniq.values(), key=lambda r: r["rel"])
    return rows


def _words(args):
    words = []
    if getattr(args, "words", None):
        words += args.words.split(",")
    if getattr(args, "words_file", None):
        with open(args.words_file, encoding="utf-8") as f:
            words += [l.strip() for l in f if l.strip() and not l.startswith("#")]
    return words or None


def cmd_missing(args):
    idx = load_index()
    rows = missing_rows(_words(args))
    mb = sum(int(r["size"] or 0) for r in rows) / 1e6
    print(f"Drive {len(idx)} videos | local {len(local_rels())} | missing {len(rows)} ({mb:,.0f} MB)")
    for r in rows[: args.show]:
        print(f"  {int(r['size'] or 0) / 1e6:6.1f} MB  {r['rel']}")


def _fetch(r, key):
    """Download one file; returns a status line. Atomic via .part + rename."""
    dst = os.path.join(SOURCE_DIR, *r["rel"].split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = f"{API}/{r['id']}?alt=media&key={key}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp, open(dst + ".part", "wb") as f:
                while chunk := resp.read(1 << 20):
                    f.write(chunk)
            os.replace(dst + ".part", dst)
            return f"ok      {r['rel']}"
        except urllib.error.HTTPError as e:
            if e.code == 403 and b"downloadQuotaExceeded" in e.read():
                return f"SKIPPED {r['rel']}  (Drive download quota hit - retry tomorrow)"
            err = f"HTTP {e.code}"
        except OSError as e:
            err = str(e)
        time.sleep(2 ** attempt)
    return f"FAILED  {r['rel']}  ({err})"


def cmd_download(args):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    key = api_key()
    rows = missing_rows(_words(args))
    if not rows:
        print("nothing to download")
        return
    total = sum(int(r["size"] or 0) for r in rows) / 1e6
    print(f"downloading {len(rows)} clip(s), {total:.0f} MB -> {SOURCE_DIR}/ "
          f"({args.parallel} at a time)", flush=True)
    failed = 0
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = [pool.submit(_fetch, r, key) for r in rows]
        for i, fut in enumerate(as_completed(futures), 1):
            line = fut.result()
            failed += not line.startswith("ok")
            print(f"  [{i}/{len(rows)}] {line}", flush=True)
    print(f"done ({failed} not downloaded) - now run: python tools/build_manifest.py")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index")
    for name in ("missing", "download"):
        p = sub.add_parser(name)
        p.add_argument("--words", help="comma-separated phrases, e.g. boy,want,thank you")
        p.add_argument("--words-file", help="one phrase per line")
        if name == "missing":
            p.add_argument("--show", type=int, default=40)
        else:
            p.add_argument("--parallel", type=int, default=4, help="simultaneous downloads")
    args = ap.parse_args()
    os.chdir(_REPO_ROOT)
    {"index": cmd_index, "missing": cmd_missing, "download": cmd_download}[args.cmd](args)


if __name__ == "__main__":
    main()
