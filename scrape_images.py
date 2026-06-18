"""Download US president portraits from presidency.ucsb.edu into images/.

Polite, idempotent (skips existing files), and tolerant (a failed portrait is
logged and skipped — the build later falls back to a generated text card).
"""
from __future__ import annotations

import csv
import difflib
import re
import time
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "data" / "presidents.csv"
IMAGES_DIR = ROOT / "images"
INDEX_URL = "https://www.presidency.ucsb.edu/presidents"
BASE = "https://www.presidency.ucsb.edu"
HEADERS = {"User-Agent": "Mozilla/5.0 (presidents-pview image scraper; contact lab1702)"}

_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
_PORTRAIT_RE = re.compile(r"/public/people/([^/?\"]+)\.(?:jpe?g|png)", re.IGNORECASE)

# Explicit stem overrides for rows whose UCSB slug is hard to fuzzy-match.
# number -> stem. Fill in after inspecting images/_manifest.csv if needed.
OVERRIDES: dict[int, str] = {
    # George H.W. Bush: UCSB slug is "george-bush" (not "george-w-bush" which is #43)
    41: "george-bush",
    # Donald Trump: use the 2nd-term portrait (more current)
    45: "donald-j-trump-2nd-term",
}


def parse_portraits(html: str) -> dict[str, dict]:
    """Map image stem -> {"url", "name"} for every president portrait on the page."""
    out: dict[str, dict] = {}
    for tag in _IMG_TAG_RE.findall(html):
        attrs = dict(_ATTR_RE.findall(tag))
        src = attrs.get("src", "")
        m = _PORTRAIT_RE.search(src)
        if not m:
            continue
        stem = m.group(1).lower()
        url = src if src.startswith("http") else BASE + src
        out[stem] = {"url": url, "name": attrs.get("alt", "").strip()}
    return out


def lastname_slug(name: str) -> str:
    """Lowercase, hyphenated last-name token, dropping middle initials/suffixes."""
    cleaned = re.sub(r"[.,]", "", name)
    parts = [p for p in cleaned.split() if p]
    # Drop a trailing generational suffix.
    while parts and parts[-1].lower() in {"jr", "sr", "ii", "iii", "iv"}:
        parts.pop()
    # Keep a nobiliary particle ("Van Buren") attached to the surname.
    if len(parts) >= 2 and parts[-2].lower() in {"van", "von", "de", "la"}:
        tail = parts[-2:]
    else:
        tail = parts[-1:]
    return "-".join(t.lower() for t in tail)


def match_row_to_stem(name: str, number: int, portraits: dict[str, dict]) -> str | None:
    """Best-matching portrait stem for a CSV row, or None."""
    if number in OVERRIDES:
        stem = OVERRIDES[number]
        return stem if stem in portraits else None
    stems = list(portraits.keys())
    target = lastname_slug(name)
    # Prefer stems that contain the surname AND share the first-name initial.
    first_initial = re.sub(r"[^a-z]", "", name.lower()[:1])
    candidates = [s for s in stems if target in s]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        better = [s for s in candidates if s.startswith(first_initial)]
        if len(better) == 1:
            return better[0]
    # Fall back to fuzzy full-name match.
    full = re.sub(r"[^a-z]+", "-", name.lower()).strip("-")
    close = difflib.get_close_matches(full, stems, n=1, cutoff=0.6)
    return close[0] if close else None


def _download(url: str, dest: Path, client: httpx.Client) -> None:
    resp = client.get(url, headers=HEADERS, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def main() -> None:
    IMAGES_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(CSV)
    with httpx.Client() as client:
        html = client.get(INDEX_URL, headers=HEADERS, follow_redirects=True, timeout=30).text
        portraits = parse_portraits(html)
        print(f"Discovered {len(portraits)} portraits on the index page.")

        manifest_rows = []
        for _, row in df.iterrows():
            number = int(row["number"])
            name = row["name"]
            dest = ROOT / row["image"]
            stem = match_row_to_stem(name, number, portraits)
            status = ""
            if stem is None:
                status = "NO MATCH"
            elif dest.exists():
                status = "skip (exists)"
            else:
                try:
                    _download(portraits[stem]["url"], dest, client)
                    status = "downloaded"
                    time.sleep(0.5)  # be polite
                except Exception as exc:  # tolerant: log and continue
                    status = f"ERROR {exc}"
            print(f"  #{number:>2} {name:<24} -> {stem or '-':<22} {status}")
            manifest_rows.append(
                {"number": number, "name": name, "stem": stem or "",
                 "url": portraits.get(stem, {}).get("url", "") if stem else "",
                 "status": status}
            )

    manifest = IMAGES_DIR / "_manifest.csv"
    with manifest.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["number", "name", "stem", "url", "status"])
        writer.writeheader()
        writer.writerows(manifest_rows)
    matched = sum(1 for r in manifest_rows if r["stem"])
    print(f"Matched {matched}/{len(manifest_rows)} rows. Manifest: {manifest}")


if __name__ == "__main__":
    main()
