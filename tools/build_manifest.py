"""Build data/manifest.csv from the ISLRTC dictionary download.

Scans data/_source/isl_dictionary/ (the Google Drive folder, extracted as-is),
turns each file name into a lowercase phrase, picks one clip per phrase, and
writes the manifest the matcher reads. The videos themselves are never copied
or committed — the manifest points straight at them.

Name parsing, in order:
  "Thank_You.mp4"                 -> "thank you"
  "Name_(Sign_2).mp4"             -> "name", variant 2 (variant 1 preferred)
  "Hair_(Curly_Hair).mp4"         -> "hair", qualified (unqualified preferred)
  "Rupee, money.mp4"              -> "rupee" and "money" (comma = synonyms)
  "I_Don_t_Know.mp4"              -> "i don't know" (split contractions rejoined)
  "Numbers/10_Ten.mp4"            -> "10" and "ten"
  "BCS/Air Fryer - English.mp4"   -> "air fryer"
Every phrase goes through matcher.normalize_phrase, so dictionary entries and
transcripts follow identical spelling rules.

Skipped: Hindi folders and non-ASCII names, regional compilations ("Some Signs
of Manipur", "Numbers 1-10 (Odisha)"), clips longer than --max-seconds, and
"(Explanation)" clips longer than --max-explanation-seconds — those are
long-form explanations, not single signs, and one of them would stall a demo.

Clips in a codec browsers can't play reliably (HEVC, MPEG-4 Part 2, MPEG-2)
are transcoded once to H.264 under data/_derived/h264/ (gitignored).

data/aliases.csv adds hand-checked extra phrases for an existing sign, e.g.
"difficult" -> the "hard difficult" clip.

Usage: python tools/build_manifest.py [--max-seconds 30] [--dry-run]
"""
import argparse
import csv
import os
import re
import sys
import time
from collections import Counter
from fractions import Fraction

import av

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from src.matcher import normalize_phrase  # noqa: E402

SOURCE_DIR = "data/_source/isl_dictionary"
DERIVED_DIR = "data/_derived/h264"
PROBE_CACHE = "data/_derived/probe_cache.csv"
ALIASES_CSV = "data/aliases.csv"
TRIMS_CSV = "data/trims.csv"
TRIMMED_DIR = "data/_derived/trimmed"
MANIFEST_CSV = "data/manifest.csv"

SOURCE_URL = "https://drive.google.com/drive/folders/1U-Pr4r1-cupgNOOq9NH_uTsQnPSVEKco"
VIDEO_EXTS = {".mp4", ".m4v", ".mpg", ".mov"}
BROWSER_SAFE_CODECS = {"h264"}
TRANSCODE_MAX_HEIGHT = 720

MANIFEST_FIELDS = ["id", "phrase", "ngram_len", "source_url", "local_path",
                   "duration_ms", "license", "notes"]

_PRONOUNS = {"i", "you", "we", "they", "he", "she", "it", "that", "there", "who", "what"}


# --- probing -----------------------------------------------------------------

def probe(path: str) -> dict:
    c = av.open(path)
    try:
        v = c.streams.video[0]
        return {
            "codec": v.codec_context.name,
            "width": v.codec_context.width,
            "height": v.codec_context.height,
            "duration_s": float(c.duration / 1e6) if c.duration else 0.0,
        }
    finally:
        c.close()


def probe_all(rel_paths: list[str]) -> dict:
    """Probe every clip, reusing cached results for unchanged files."""
    cache = {}
    if os.path.exists(PROBE_CACHE):
        with open(PROBE_CACHE, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                cache[r["rel"]] = r

    results, fresh = {}, 0
    for rel in rel_paths:
        full = os.path.join(SOURCE_DIR, rel)
        st = os.stat(full)
        key = (str(st.st_size), str(int(st.st_mtime)))
        hit = cache.get(rel)
        if hit and (hit["size"], hit["mtime"]) == key:
            info = {"codec": hit["codec"], "width": int(hit["width"]),
                    "height": int(hit["height"]), "duration_s": float(hit["duration_s"])}
        else:
            try:
                info = probe(full)
            except Exception as e:  # corrupt / partial download
                info = {"codec": "", "width": 0, "height": 0, "duration_s": 0.0,
                        "error": repr(e)}
            fresh += 1
        info["size"], info["mtime"] = key
        results[rel] = info

    os.makedirs(os.path.dirname(PROBE_CACHE), exist_ok=True)
    with open(PROBE_CACHE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rel", "size", "mtime", "codec", "width", "height", "duration_s"])
        for rel, i in results.items():
            if "error" not in i:
                w.writerow([rel, i["size"], i["mtime"], i["codec"], i["width"],
                            i["height"], i["duration_s"]])
    print(f"probed {len(rel_paths)} clips ({fresh} new, {len(rel_paths) - fresh} cached)")
    return results


# --- name parsing ------------------------------------------------------------

def _rejoin_contractions(words: list[str]) -> list[str]:
    """Undo the dictionary's apostrophe-to-underscore mangling: Don_t -> Don't."""
    out = []
    for w in words:
        if out and w.lower() == "t" and out[-1].lower().endswith("n"):
            out[-1] += "'t"
        elif out and w == "s" and out[-1].isalpha() and len(out[-1]) > 1:
            out[-1] += "'s"
        elif out and w in ("ll", "re", "ve", "m", "d") and out[-1].lower() in _PRONOUNS:
            out[-1] += "'" + w
        else:
            out.append(w)
    return out


def _to_phrase(text: str) -> str:
    text = text.replace("&", " and ")
    words = [w for w in re.split(r"[_\s]+", text) if w]
    return normalize_phrase(" ".join(_rejoin_contractions(words)))


def parse_name(rel: str):
    """Return (list of candidate dicts, skip_reason). Exactly one is non-empty."""
    parts = rel.split("/")
    folder = parts[0] if len(parts) > 1 else ""
    stem = os.path.splitext(parts[-1])[0].strip()

    if "Hindi" in parts[:-1] or any(ord(ch) > 127 for ch in stem.replace("°", "")):
        return [], "non-English"
    if re.match(r"(?i)some[_ ]signs[_ ]of", stem) or re.match(r"(?i)numbers[_ ]", stem):
        return [], "regional compilation"

    stem = re.sub(r"\s+-\s+English$", "", stem)

    variant = 1
    m = re.search(r"\)_(\d+)$", stem)          # "bat (sports)_2"
    if m:
        variant = int(m.group(1))
        stem = stem[:m.start() + 1]

    explanation, qualifiers = False, []
    for q in re.findall(r"\(([^)]*)\)", stem):
        qm = re.fullmatch(r"(?i)\s*sign(?:[_ ]*(\d+))?\s*", q)
        if qm:
            variant = int(qm.group(1) or 1)
        elif re.search(r"(?i)expla(?:i)?nation|example", q):
            explanation = True
        else:
            qualifiers.append(q.replace("_", " ").strip())
    main = re.sub(r"\([^)]*\)", " ", stem).strip(" _")

    phrases = []
    if folder == "Numbers":
        nm = re.fullmatch(r"(\d+)_(.+)", main)
        if nm:
            phrases = [(nm.group(1), False), (_to_phrase(nm.group(2)), False)]
    if not phrases:
        pieces = [p for p in main.split(",") if p.strip()]
        phrases = [(_to_phrase(p), len(pieces) > 1) for p in pieces]

    cands = [{
        "phrase": ph, "rel": rel, "variant": variant, "explanation": explanation,
        "qualifiers": qualifiers, "from_synonym": syn,
    } for ph, syn in phrases if ph]
    return (cands, None) if cands else ([], "empty name")


def _priority(c: dict):
    # Lower is better: a plain single-word file beats a synonym list, an
    # unqualified sign beats "(Academic)", sign 1 beats sign 2, shorter wins.
    return (c["explanation"], c["from_synonym"], bool(c["qualifiers"]),
            c["variant"], c["duration_s"], c["rel"])


# --- transcoding -------------------------------------------------------------

def transcode_h264(src: str, dst: str, start_s: float | None = None,
                   end_s: float | None = None) -> None:
    """Re-encode to browser-safe H.264 (<=720p, no audio, faststart),
    optionally keeping only [start_s, end_s]."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".part"
    inp = av.open(src)
    vin = inp.streams.video[0]
    vin.thread_type = "AUTO"

    w, h = vin.codec_context.width, vin.codec_context.height
    if h > TRANSCODE_MAX_HEIGHT:
        w, h = round(w * TRANSCODE_MAX_HEIGHT / h), TRANSCODE_MAX_HEIGHT
    w, h = w - w % 2, h - h % 2

    out = av.open(tmp, "w", format="mp4", options={"movflags": "+faststart"})
    rate = int(round(float(vin.average_rate or 25)))
    vout = out.add_stream("libx264", rate=rate)
    vout.width, vout.height, vout.pix_fmt = w, h, "yuv420p"
    vout.options = {"crf": "23", "preset": "veryfast"}

    # Explicit constant-rate timestamps: letting the encoder infer them
    # (pts=None) produces non-monotonic DTS on some HEVC sources and the
    # muxer rejects the packet.
    time_base = Fraction(1, rate)
    i = 0
    for frame in inp.decode(vin):
        t = float(frame.pts * vin.time_base) if frame.pts is not None else i / rate
        if start_s is not None and t < start_s:
            continue
        if end_s is not None and t > end_s:
            break
        frame = frame.reformat(width=w, height=h, format="yuv420p")
        frame.pts, frame.time_base = i, time_base
        i += 1
        for packet in vout.encode(frame):
            out.mux(packet)
    for packet in vout.encode():
        out.mux(packet)
    out.close()
    inp.close()
    os.replace(tmp, dst)


def derived_path(rel: str) -> str:
    return f"{DERIVED_DIR}/{os.path.splitext(rel)[0]}.mp4"


def trimmed_path(rel: str, start_s: float, end_s: float) -> str:
    return f"{TRIMMED_DIR}/{os.path.splitext(rel)[0]}__{start_s:g}-{end_s:g}.mp4"


def load_trims() -> list[dict]:
    """Human-verified cuts of long explanation videos (data/trims.csv).

    Explanation videos sign the word inside example sentences with no pause,
    so the sign's position cannot be found automatically - a wrong cut would
    show a wrong sign. Only rows with verified_by filled in are used.
    """
    if not os.path.exists(TRIMS_CSV):
        return []
    out = []
    with open(TRIMS_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("verified_by", "").strip():
                continue
            start_s, end_s = float(r["start_s"]), float(r["end_s"])
            if not 0 <= start_s < end_s or end_s - start_s > 10:
                print(f"  trim ignored (bad range {start_s}-{end_s}): {r['rel']}")
                continue
            out.append({"rel": r["rel"].strip(), "start_s": start_s, "end_s": end_s,
                        "verified_by": r["verified_by"].strip()})
    return out


# --- main --------------------------------------------------------------------

def slug(phrase: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", phrase).strip("_") or "x"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--max-seconds", type=float, default=30.0,
                    help="skip clips longer than this (default 30)")
    ap.add_argument("--max-explanation-seconds", type=float, default=8.0,
                    help="skip '(Explanation)' clips longer than this (default 8)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; don't transcode or write the manifest")
    args = ap.parse_args()
    os.chdir(_REPO_ROOT)

    if not os.path.isdir(SOURCE_DIR):
        sys.exit(f"{SOURCE_DIR}/ not found - extract the ISL Dictionary Drive folder there first.")

    rels = sorted(
        os.path.relpath(os.path.join(dp, fn), SOURCE_DIR).replace(os.sep, "/")
        for dp, _, fns in os.walk(SOURCE_DIR) for fn in fns
        if os.path.splitext(fn)[1].lower() in VIDEO_EXTS
    )
    info = probe_all(rels)

    skipped = Counter()
    by_phrase: dict[str, list] = {}
    for rel in rels:
        meta = info[rel]
        if "error" in meta:
            skipped["unreadable"] += 1
            print(f"  unreadable, skipped: {rel}  {meta['error']}")
            continue
        cands, reason = parse_name(rel)
        if reason:
            skipped[reason] += 1
            continue
        if meta["duration_s"] > args.max_seconds:
            skipped[f"longer than {args.max_seconds:g}s"] += 1
            continue
        # "How_(Explanation).mp4" is a 19s lecture, not a sign: it would turn a
        # five-word sentence into half a minute. Short ones are just the sign.
        if cands[0]["explanation"] and meta["duration_s"] > args.max_explanation_seconds:
            skipped[f"explanation longer than {args.max_explanation_seconds:g}s"] += 1
            continue
        for c in cands:
            c.update(meta)
            by_phrase.setdefault(c["phrase"], []).append(c)

    for t in load_trims():
        if not os.path.exists(os.path.join(SOURCE_DIR, t["rel"])):
            print(f"  trim skipped, source not downloaded: {t['rel']}")
            continue
        cands, _ = parse_name(t["rel"])
        for c in cands:
            # A verified cut is a plain single sign, whatever the source was.
            c.update({"explanation": False, "codec": "trimmed",
                      "duration_s": t["end_s"] - t["start_s"], "trim": t})
            by_phrase.setdefault(c["phrase"], []).append(c)

    chosen = {ph: min(cs, key=_priority) for ph, cs in by_phrase.items()}

    trims_needed = {(c["rel"], c["trim"]["start_s"], c["trim"]["end_s"])
                    for c in chosen.values() if "trim" in c}
    for rel, a, b in sorted(trims_needed):
        if not os.path.exists(trimmed_path(rel, a, b)) and not args.dry_run:
            transcode_h264(os.path.join(SOURCE_DIR, rel), trimmed_path(rel, a, b), a, b)
            print(f"  trimmed {rel} [{a:g}s-{b:g}s]")

    # Transcode only the clips that were actually chosen and aren't browser-safe.
    to_transcode = sorted({c["rel"] for c in chosen.values()
                           if c["codec"] not in BROWSER_SAFE_CODECS and "trim" not in c
                           and not os.path.exists(derived_path(c["rel"]))})
    if to_transcode and not args.dry_run:
        print(f"transcoding {len(to_transcode)} clip(s) to H.264 -> {DERIVED_DIR}/")
        for i, rel in enumerate(to_transcode, 1):
            t0 = time.perf_counter()
            transcode_h264(os.path.join(SOURCE_DIR, rel), derived_path(rel))
            print(f"  [{i}/{len(to_transcode)}] {rel}  ({time.perf_counter() - t0:.1f}s)")

    rows, used_ids = [], set()

    def add_row(phrase, local_path, duration_s, notes):
        rid, n = slug(phrase), 2
        while rid in used_ids:
            rid, n = f"{slug(phrase)}_{n}", n + 1
        used_ids.add(rid)
        rows.append({
            "id": rid, "phrase": phrase, "ngram_len": len(phrase.split()),
            "source_url": SOURCE_URL, "local_path": local_path,
            "duration_ms": int(round(duration_s * 1000)), "license": "ISLRTC",
            "notes": notes,
        })

    for phrase in sorted(chosen):
        c = chosen[phrase]
        if "trim" in c:
            t = c["trim"]
            local = trimmed_path(c["rel"], t["start_s"], t["end_s"])
            note = (f"src={c['rel']}; trimmed {t['start_s']:g}-{t['end_s']:g}s, "
                    f"verified by {t['verified_by']}")
        elif c["codec"] in BROWSER_SAFE_CODECS:
            local = f"{SOURCE_DIR}/{c['rel']}"
            note = f"src={c['rel']}"
        else:
            local = derived_path(c["rel"])
            note = f"src={c['rel']}; transcoded from {c['codec']}"
        alts = len(by_phrase[phrase]) - 1
        if alts:
            note += f"; {alts} other variant(s)"
        add_row(phrase, local, c["duration_s"], note)

    n_alias = 0
    if os.path.exists(ALIASES_CSV):
        by_text = {r["phrase"]: r for r in rows}
        with open(ALIASES_CSV, newline="", encoding="utf-8") as f:
            for a in csv.DictReader(f):
                alias, target = normalize_phrase(a["alias"]), normalize_phrase(a["target"])
                if alias in by_text:
                    print(f"  alias {alias!r} ignored: the dictionary already has its own sign")
                    continue
                if target not in by_text:
                    print(f"  alias {alias!r} ignored: target {target!r} not in manifest")
                    continue
                t = by_text[target]
                add_row(alias, t["local_path"], t["duration_ms"] / 1000,
                        f"alias of {target!r}: {a.get('reason', '')}".strip())
                by_text[alias] = rows[-1]
                n_alias += 1

    rows.sort(key=lambda r: r["phrase"])
    lens = Counter(r["ngram_len"] for r in rows)
    print(f"\n{len(rels)} files -> {len(chosen)} phrases (+{n_alias} aliases) = {len(rows)} manifest rows")
    print("skipped:", dict(skipped) or "none")
    print("phrase lengths (words: count):", dict(sorted(lens.items())))

    if args.dry_run:
        print("dry run - manifest not written")
        return
    with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {MANIFEST_CSV}")


if __name__ == "__main__":
    main()
