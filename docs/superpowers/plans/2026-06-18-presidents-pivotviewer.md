# US Presidents PivotViewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable, single-file `presidents.html` PivotViewer of all US presidents from a curated dataset plus scraped portraits, using the `pview` package.

**Architecture:** A curated CSV (`data/presidents.csv`) is the source of truth for facts. `scrape_images.py` downloads portraits from presidency.ucsb.edu into `images/`, matching each portrait to a CSV row. `build.py` loads the CSV with pandas and calls `pview.build(..., single_file=True)` to emit the viewer. The pieces are decoupled: a missing image degrades to pview's generated text card, never a hard failure.

**Tech Stack:** Python 3.11+ (3.14 local), pandas, pillow, httpx (all already pview deps), `pview` (installed editable from `/home/lab/tmp/pview`), pytest for tests. Scraper uses stdlib `re`, `csv`, `difflib` — no extra HTML-parsing dependency.

## Global Constraints

- Python 3.11+ (3.14 available locally).
- Only these runtime deps: `pview`, `pandas`, `pillow`, `httpx`. No `beautifulsoup4`/`lxml` — parse with stdlib `re`.
- All commands run from the project root `/home/lab/tmp/presidents_pv`.
- One row per **person** (Grover Cleveland and Donald Trump each appear once, despite non-consecutive terms), consistent with the approved spec. `number` = the person's **first** presidency ordinal; the `terms` column records the full term history.
- `age_at_inauguration` is age at the person's **first** inauguration.
- Dates are ISO `YYYY-MM-DD`. Blank `term_end`/`date_of_death`/`age_at_death` mean "still in office" / "living".
- Image paths in the CSV are deterministic: `images/{number:02d}_{lastname}.jpg` (e.g. `images/01_washington.jpg`).
- Scraper must be polite (real User-Agent, delay between downloads), idempotent (skip existing files), and tolerant (log and skip failures; never abort the run).

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `README.md`
- Create: `tests/__init__.py` (empty)
- Modify: `.gitignore` (append build artifacts)

**Interfaces:**
- Produces: the directory layout and dependency manifest later tasks rely on. No code symbols.

- [ ] **Step 1: Create `requirements.txt`**

```
# Runtime
pandas
pillow
httpx
# pview is installed editable from /home/lab/tmp/pview:
#   pip install -e /home/lab/tmp/pview
# Dev
pytest
```

- [ ] **Step 2: Append build artifacts to `.gitignore`**

The file already contains `__pycache__/`, `*.pyc`, `.cache/`. Append:

```
build_out/
images/_manifest.csv
.pytest_cache/
```

(Note: `images/*.jpg` and `presidents.html` ARE committed — they are deliverables.)

- [ ] **Step 3: Create `README.md`**

```markdown
# US Presidents PivotViewer

An interactive [pview](https://github.com/lab1702/pview) collection viewer of US
presidents. Sort, group, and filter by party, birth state, age at inauguration,
date of birth, presidency order, lifespan, and more.

## Layout

- `data/presidents.csv` — curated dataset (one row per president)
- `scrape_images.py` — downloads portraits from presidency.ucsb.edu into `images/`
- `build.py` — builds the portable viewer `presidents.html`
- `presidents.html` — the output; open it in any browser

## Rebuild from scratch

```bash
pip install -e /home/lab/tmp/pview      # installs pview + pandas/pillow/httpx
pip install -r requirements.txt
python scrape_images.py                 # populates images/ (skips existing)
python build.py                         # writes presidents.html
```

Then open `presidents.html`.

## Notes

- Grover Cleveland (22nd & 24th) and Donald Trump (45th & 47th) each appear as a
  single card; their `terms` field records the non-consecutive terms.
- A portrait that can't be fetched falls back to a generated text card, so the
  viewer always builds.
```

- [ ] **Step 4: Create empty `tests/__init__.py`**

```python
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt README.md tests/__init__.py .gitignore
git commit -m "chore: scaffold presidents pivotviewer project"
```

---

### Task 2: Curated dataset + validation test

**Files:**
- Create: `data/presidents.csv`
- Create: `tests/test_data.py`

**Interfaces:**
- Produces: `data/presidents.csv` with header
  `number,name,party,term_start,term_end,terms,birth_state,date_of_birth,age_at_inauguration,date_of_death,age_at_death,living,image`
  — 45 data rows. Consumed by `scrape_images.py` (Task 3) and `build.py` (Task 4).

- [ ] **Step 1: Write the failing test `tests/test_data.py`**

```python
import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

CSV = Path(__file__).resolve().parents[1] / "data" / "presidents.csv"

EXPECTED_COLUMNS = [
    "number", "name", "party", "term_start", "term_end", "terms",
    "birth_state", "date_of_birth", "age_at_inauguration",
    "date_of_death", "age_at_death", "living", "image",
]


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CSV)


def test_columns_exact(df):
    assert list(df.columns) == EXPECTED_COLUMNS


def test_row_count(df):
    # 47 presidencies minus Cleveland and Trump counted once each = 45 people.
    assert len(df) == 45


def test_number_unique_and_in_range(df):
    assert df["number"].is_unique
    assert df["number"].min() == 1
    assert df["number"].max() == 46  # Biden is 46th; Trump's row is numbered 45


def test_name_unique(df):
    assert df["name"].is_unique


def test_living_values(df):
    assert set(df["living"].unique()) <= {"Yes", "No"}


def test_dates_parse(df):
    parsed = pd.to_datetime(df["date_of_birth"], format="%Y-%m-%d")
    assert parsed.notna().all()


def test_image_paths_match_convention(df):
    for _, row in df.iterrows():
        assert row["image"].startswith("images/")
        assert row["image"].endswith(".jpg")
        assert f"{int(row['number']):02d}_" in row["image"]


def test_inauguration_ages_reasonable(df):
    assert df["age_at_inauguration"].between(40, 80).all()


def test_known_spot_values(df):
    by_name = df.set_index("name")
    assert by_name.loc["George Washington", "age_at_inauguration"] == 57
    assert by_name.loc["Theodore Roosevelt", "age_at_inauguration"] == 42  # youngest
    assert by_name.loc["Joe Biden", "term_start"] == 2021
    # Living presidents have blank death fields:
    assert pd.isna(by_name.loc["Barack Obama", "date_of_death"])
    assert by_name.loc["Barack Obama", "living"] == "Yes"


def test_living_consistency(df):
    # living == "No"  <=> has a death date
    has_death = df["date_of_death"].notna()
    is_dead = df["living"] == "No"
    assert (has_death == is_dead).all()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_data.py -v`
Expected: FAIL — `data/presidents.csv` does not exist yet (FileNotFoundError).

- [ ] **Step 3: Create `data/presidents.csv` with the curated baseline**

Use this content verbatim as the baseline. **Before committing, verify the soft spots** (Step 4) — historical facts must be correct.

```csv
number,name,party,term_start,term_end,terms,birth_state,date_of_birth,age_at_inauguration,date_of_death,age_at_death,living,image
1,George Washington,Unaffiliated,1789,1797,1789–1797,Virginia,1732-02-22,57,1799-12-14,67,No,images/01_washington.jpg
2,John Adams,Federalist,1797,1801,1797–1801,Massachusetts,1735-10-30,61,1826-07-04,90,No,images/02_adams.jpg
3,Thomas Jefferson,Democratic-Republican,1801,1809,1801–1809,Virginia,1743-04-13,57,1826-07-04,83,No,images/03_jefferson.jpg
4,James Madison,Democratic-Republican,1809,1817,1809–1817,Virginia,1751-03-16,57,1836-06-28,85,No,images/04_madison.jpg
5,James Monroe,Democratic-Republican,1817,1825,1817–1825,Virginia,1758-04-28,58,1831-07-04,73,No,images/05_monroe.jpg
6,John Quincy Adams,Democratic-Republican,1825,1829,1825–1829,Massachusetts,1767-07-11,57,1848-02-23,80,No,images/06_adams.jpg
7,Andrew Jackson,Democratic,1829,1837,1829–1837,South Carolina,1767-03-15,61,1845-06-08,78,No,images/07_jackson.jpg
8,Martin Van Buren,Democratic,1837,1841,1837–1841,New York,1782-12-05,54,1862-07-24,79,No,images/08_van-buren.jpg
9,William Henry Harrison,Whig,1841,1841,1841,Virginia,1773-02-09,68,1841-04-04,68,No,images/09_harrison.jpg
10,John Tyler,Whig,1841,1845,1841–1845,Virginia,1790-03-29,51,1862-01-18,71,No,images/10_tyler.jpg
11,James K. Polk,Democratic,1845,1849,1845–1849,North Carolina,1795-11-02,49,1849-06-15,53,No,images/11_polk.jpg
12,Zachary Taylor,Whig,1849,1850,1849–1850,Virginia,1784-11-24,64,1850-07-09,65,No,images/12_taylor.jpg
13,Millard Fillmore,Whig,1850,1853,1850–1853,New York,1800-01-07,50,1874-03-08,74,No,images/13_fillmore.jpg
14,Franklin Pierce,Democratic,1853,1857,1853–1857,New Hampshire,1804-11-23,48,1869-10-08,64,No,images/14_pierce.jpg
15,James Buchanan,Democratic,1857,1861,1857–1861,Pennsylvania,1791-04-23,65,1868-06-01,77,No,images/15_buchanan.jpg
16,Abraham Lincoln,Republican,1861,1865,1861–1865,Kentucky,1809-02-12,52,1865-04-15,56,No,images/16_lincoln.jpg
17,Andrew Johnson,National Union,1865,1869,1865–1869,North Carolina,1808-12-29,56,1875-07-31,66,No,images/17_johnson.jpg
18,Ulysses S. Grant,Republican,1869,1877,1869–1877,Ohio,1822-04-27,46,1885-07-23,63,No,images/18_grant.jpg
19,Rutherford B. Hayes,Republican,1877,1881,1877–1881,Ohio,1822-10-04,54,1893-01-17,70,No,images/19_hayes.jpg
20,James A. Garfield,Republican,1881,1881,1881,Ohio,1831-11-19,49,1881-09-19,49,No,images/20_garfield.jpg
21,Chester A. Arthur,Republican,1881,1885,1881–1885,Vermont,1829-10-05,51,1886-11-18,57,No,images/21_arthur.jpg
22,Grover Cleveland,Democratic,1885,1897,"1885–1889, 1893–1897",New Jersey,1837-03-18,47,1908-06-24,71,No,images/22_cleveland.jpg
23,Benjamin Harrison,Republican,1889,1893,1889–1893,Ohio,1833-08-20,55,1901-03-13,67,No,images/23_harrison.jpg
25,William McKinley,Republican,1897,1901,1897–1901,Ohio,1843-01-29,54,1901-09-14,58,No,images/25_mckinley.jpg
26,Theodore Roosevelt,Republican,1901,1909,1901–1909,New York,1858-10-27,42,1919-01-06,60,No,images/26_roosevelt.jpg
27,William Howard Taft,Republican,1909,1913,1909–1913,Ohio,1857-09-15,51,1930-03-08,72,No,images/27_taft.jpg
28,Woodrow Wilson,Democratic,1913,1921,1913–1921,Virginia,1856-12-28,56,1924-02-03,67,No,images/28_wilson.jpg
29,Warren G. Harding,Republican,1921,1923,1921–1923,Ohio,1865-11-02,55,1923-08-02,57,No,images/29_harding.jpg
30,Calvin Coolidge,Republican,1923,1929,1923–1929,Vermont,1872-07-04,51,1933-01-05,60,No,images/30_coolidge.jpg
31,Herbert Hoover,Republican,1929,1933,1929–1933,Iowa,1874-08-10,54,1964-10-20,90,No,images/31_hoover.jpg
32,Franklin D. Roosevelt,Democratic,1933,1945,1933–1945,New York,1882-01-30,51,1945-04-12,63,No,images/32_roosevelt.jpg
33,Harry S. Truman,Democratic,1945,1953,1945–1953,Missouri,1884-05-08,60,1972-12-26,88,No,images/33_truman.jpg
34,Dwight D. Eisenhower,Republican,1953,1961,1953–1961,Texas,1890-10-14,62,1969-03-28,78,No,images/34_eisenhower.jpg
35,John F. Kennedy,Democratic,1961,1963,1961–1963,Massachusetts,1917-05-29,43,1963-11-22,46,No,images/35_kennedy.jpg
36,Lyndon B. Johnson,Democratic,1963,1969,1963–1969,Texas,1908-08-27,55,1973-01-22,64,No,images/36_johnson.jpg
37,Richard Nixon,Republican,1969,1974,1969–1974,California,1913-01-09,56,1994-04-22,81,No,images/37_nixon.jpg
38,Gerald Ford,Republican,1974,1977,1974–1977,Nebraska,1913-07-14,61,2006-12-26,93,No,images/38_ford.jpg
39,Jimmy Carter,Democratic,1977,1981,1977–1981,Georgia,1924-10-01,52,2024-12-29,100,No,images/39_carter.jpg
40,Ronald Reagan,Republican,1981,1989,1981–1989,Illinois,1911-02-06,69,2004-06-05,93,No,images/40_reagan.jpg
41,George H. W. Bush,Republican,1989,1993,1989–1993,Massachusetts,1924-06-12,64,2018-11-30,94,No,images/41_bush.jpg
42,Bill Clinton,Democratic,1993,2001,1993–2001,Arkansas,1946-08-19,46,,,Yes,images/42_clinton.jpg
43,George W. Bush,Republican,2001,2009,2001–2009,Connecticut,1946-07-06,54,,,Yes,images/43_bush.jpg
44,Barack Obama,Democratic,2009,2017,2009–2017,Hawaii,1961-08-04,47,,,Yes,images/44_obama.jpg
45,Donald Trump,Republican,2017,,"2017–2021, 2025–present",New York,1946-06-14,70,,,Yes,images/45_trump.jpg
46,Joe Biden,Democratic,2021,2025,2021–2025,Pennsylvania,1942-11-20,78,,,Yes,images/46_biden.jpg
```

- [ ] **Step 4: Verify the soft spots against a reliable source**

Spot-check these fields with WebSearch/WebFetch (UCSB president pages or another authoritative source) and correct the CSV if any differ:
- Andrew Jackson birth state (Waxhaws — conventionally **South Carolina**).
- Andrew Johnson party label (elected on the **National Union** ticket; some sources list **Democratic**).
- George Washington party (**Unaffiliated** / no party).
- Jimmy Carter death date/age (`2024-12-29`, age 100) and `living=No`.
- That every `age_at_inauguration` is age at the person's FIRST inauguration.

Make corrections inline; do not change the column order or the 45-row count.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_data.py -v`
Expected: PASS (all assertions).

- [ ] **Step 6: Commit**

```bash
git add data/presidents.csv tests/test_data.py
git commit -m "feat: add curated presidents dataset with validation tests"
```

---

### Task 3: Image scraper

**Files:**
- Create: `scrape_images.py`
- Create: `tests/test_scrape.py`

**Interfaces:**
- Consumes: `data/presidents.csv` (columns `number`, `name`, `image`).
- Produces (importable from `scrape_images`):
  - `parse_portraits(html: str) -> dict[str, dict]` — maps a lowercased image **stem** (filename without extension) to `{"url": str, "name": str}`.
  - `lastname_slug(name: str) -> str` — lowercased last-name token used for matching (e.g. `"Martin Van Buren" -> "van-buren"`, `"James K. Polk" -> "polk"`).
  - `match_row_to_stem(name, number, portraits) -> str | None` — returns the best-matching stem for a CSV row, or `None`.
  - `main()` — fetches the index, downloads matched portraits into `images/`, writes `images/_manifest.csv`.

- [ ] **Step 1: Write the failing test `tests/test_scrape.py`**

```python
import scrape_images as s

SAMPLE_HTML = '''
<a href="/people/president/george-washington">
  <img alt="George Washington" src="https://www.presidency.ucsb.edu/sites/default/files/styles/large/public/people/george-washington.jpg?itok=abc123">
  George Washington
</a>
<a href="/people/president/martin-van-buren">
  <img src="/sites/default/files/styles/large/public/people/martin-van-buren.jpg?itok=xy" alt="Martin Van Buren">
</a>
<a href="/about"><img src="/sites/default/files/logo.png" alt="logo"></a>
'''


def test_parse_portraits_finds_people_images_only():
    out = s.parse_portraits(SAMPLE_HTML)
    assert set(out.keys()) == {"george-washington", "martin-van-buren"}
    assert out["george-washington"]["url"].startswith("https://")
    assert out["george-washington"]["url"].endswith("itok=abc123")
    assert out["george-washington"]["name"] == "George Washington"


def test_parse_portraits_absolutizes_relative_src():
    out = s.parse_portraits(SAMPLE_HTML)
    assert out["martin-van-buren"]["url"].startswith(
        "https://www.presidency.ucsb.edu/sites/default/files"
    )


def test_lastname_slug():
    assert s.lastname_slug("George Washington") == "washington"
    assert s.lastname_slug("Martin Van Buren") == "van-buren"
    assert s.lastname_slug("James K. Polk") == "polk"
    assert s.lastname_slug("George H. W. Bush") == "bush"


def test_match_row_to_stem():
    portraits = s.parse_portraits(SAMPLE_HTML)
    assert s.match_row_to_stem("George Washington", 1, portraits) == "george-washington"
    assert s.match_row_to_stem("Martin Van Buren", 8, portraits) == "martin-van-buren"
    assert s.match_row_to_stem("Nonexistent Person", 99, portraits) is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_scrape.py -v`
Expected: FAIL — `No module named 'scrape_images'`.

- [ ] **Step 3: Write `scrape_images.py`**

```python
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
OVERRIDES: dict[int, str] = {}


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
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `python -m pytest tests/test_scrape.py -v`
Expected: PASS (all four tests; no network access — they only exercise pure functions).

- [ ] **Step 5: Run the scraper against the live site**

Run: `python scrape_images.py`
Expected: prints "Discovered N portraits" (N ≈ 45–47), a per-president line each, and "Matched M/45 rows". Inspect output: if any row shows `NO MATCH`, open `images/_manifest.csv`, find the correct stem from the discovered portraits, and add it to the `OVERRIDES` dict (e.g. `OVERRIDES = {45: "donald-trump"}`), then re-run. Re-running skips already-downloaded files.

- [ ] **Step 6: Verify images landed**

Run: `ls images/*.jpg | wc -l`
Expected: close to 45 (a few misses are acceptable — they degrade to text cards). Spot-check one opens as a real image: `python -c "from PIL import Image; print(Image.open('images/01_washington.jpg').size)"`

- [ ] **Step 7: Commit**

```bash
git add scrape_images.py tests/test_scrape.py images/*.jpg
git commit -m "feat: add portrait scraper and download president images"
```

---

### Task 4: Build script

**Files:**
- Create: `build.py`
- Create: `tests/test_build.py`

**Interfaces:**
- Consumes: `data/presidents.csv`; `pview.build`.
- Produces (importable from `build`):
  - `FACETS: dict[str, str]` — explicit facet classification passed to pview.
  - `load_df(csv_path) -> pandas.DataFrame` — reads the CSV, parsing date columns to datetime so pview classifies them as `date`.
  - `validate(df) -> None` — raises `ValueError` if expected columns are missing or `number`/`name` are not unique.
  - `build_viewer(df, out_dir="build_out", html_out="presidents.html") -> pathlib.Path` — calls `pview.build(single_file=True)` and copies the result to `html_out`; returns the `html_out` path.
  - `main()`.

- [ ] **Step 1: Write the failing test `tests/test_build.py`**

```python
from pathlib import Path

import pandas as pd
import pytest

import build


def _minimal_df(tmp_path: Path) -> pd.DataFrame:
    img = tmp_path / "x.png"
    from PIL import Image
    Image.new("RGB", (8, 8), "navy").save(img)
    return pd.DataFrame({
        "number": [1, 2],
        "name": ["Ada", "Bob"],
        "party": ["X", "Y"],
        "term_start": [1789, 1797],
        "term_end": [1797, 1801],
        "terms": ["1789–1797", "1797–1801"],
        "birth_state": ["VA", "MA"],
        "date_of_birth": pd.to_datetime(["1732-02-22", "1735-10-30"]),
        "age_at_inauguration": [57, 61],
        "date_of_death": pd.to_datetime(["1799-12-14", "1826-07-04"]),
        "age_at_death": [67, 90],
        "living": ["No", "No"],
        "image": [str(img), str(img)],
    })


def test_validate_passes_on_good_df(tmp_path):
    build.validate(_minimal_df(tmp_path))  # should not raise


def test_validate_rejects_missing_column(tmp_path):
    df = _minimal_df(tmp_path).drop(columns=["party"])
    with pytest.raises(ValueError, match="party"):
        build.validate(df)


def test_validate_rejects_duplicate_number(tmp_path):
    df = _minimal_df(tmp_path)
    df.loc[1, "number"] = 1
    with pytest.raises(ValueError, match="number"):
        build.validate(df)


def test_load_df_parses_dates():
    df = build.load_df(build.CSV)
    assert pd.api.types.is_datetime64_any_dtype(df["date_of_birth"])


def test_build_viewer_emits_html(tmp_path):
    df = _minimal_df(tmp_path)
    out = build.build_viewer(
        df, out_dir=str(tmp_path / "out"), html_out=str(tmp_path / "viewer.html")
    )
    assert out.exists()
    assert out.stat().st_size > 1000  # single-file inlines assets -> non-trivial
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_build.py -v`
Expected: FAIL — `No module named 'build'`.

- [ ] **Step 3: Write `build.py`**

```python
"""Build the portable presidents.html PivotViewer from data/presidents.csv."""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from pview import build as pview_build

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "data" / "presidents.csv"

DATE_COLS = ["date_of_birth", "date_of_death"]
EXPECTED_COLUMNS = [
    "number", "name", "party", "term_start", "term_end", "terms",
    "birth_state", "date_of_birth", "age_at_inauguration",
    "date_of_death", "age_at_death", "living", "image",
]

# Lock pview's facet classification (name -> text default; image excluded).
FACETS = {
    "party": "category",
    "birth_state": "category",
    "living": "category",
    "date_of_birth": "date",
    "date_of_death": "date",
    "number": "numeric",
    "term_start": "numeric",
    "term_end": "numeric",
    "age_at_inauguration": "numeric",
    "age_at_death": "numeric",
}

CARD_FIELDS = ["name", "party", "terms"]


def load_df(csv_path=CSV) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
    return df


def validate(df: pd.DataFrame) -> None:
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing expected columns: {missing}")
    if not df["number"].is_unique:
        raise ValueError("number column must be unique")
    if not df["name"].is_unique:
        raise ValueError("name column must be unique")


def build_viewer(df: pd.DataFrame, out_dir="build_out",
                 html_out="presidents.html") -> Path:
    facets = {k: v for k, v in FACETS.items() if k in df.columns}
    pview_build(
        df,
        name_col="name",
        image_col="image",
        card_fields=[c for c in CARD_FIELDS if c in df.columns],
        facets=facets,
        title="US Presidents",
        out_dir=out_dir,
        single_file=True,
    )
    produced = Path(out_dir) / "index.html"
    html_out = Path(html_out)
    shutil.copyfile(produced, html_out)
    return html_out


def main() -> None:
    df = load_df()
    validate(df)
    out = build_viewer(df)
    print(f"Built viewer -> {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_build.py -v`
Expected: PASS. If `test_build_viewer_emits_html` fails because pview writes the single file under a different name than `index.html`, inspect the `out_dir` contents (`ls`) and update the `produced = Path(out_dir) / "index.html"` line in `build_viewer` to the actual filename, then re-run.

- [ ] **Step 5: Commit**

```bash
git add build.py tests/test_build.py
git commit -m "feat: add pview build script with validation tests"
```

---

### Task 5: End-to-end build, verification, and finalize

**Files:**
- Create: `presidents.html` (generated output, committed)

**Interfaces:**
- Consumes: everything from Tasks 1–4.

- [ ] **Step 1: Run the full pipeline**

Run:
```bash
python scrape_images.py && python build.py
```
Expected: scraper reports matches; build prints `Built viewer -> presidents.html (… bytes)` with a multi-hundred-KB-or-larger size (single-file inlines the portraits).

- [ ] **Step 2: Report the build summary**

The build uses `pview.build` (which wraps `build_with_summary`). To see image-error counts, run this one-off and report the numbers:
```bash
python -c "
import build
from pview import build_with_summary
df = build.load_df(); build.validate(df)
_, summary = build_with_summary(df, name_col='name', image_col='image',
    card_fields=build.CARD_FIELDS, facets={k:v for k,v in build.FACETS.items() if k in df.columns},
    title='US Presidents', out_dir='build_out', single_file=True)
print(summary)
"
```
Expected: `n_items=45`, `n_image_errors` low (ideally 0). If `n_generated` is high, revisit the scraper matching (Task 3, Step 5).

- [ ] **Step 3: Sanity-check the output HTML**

Run: `python -c "import pathlib; h=pathlib.Path('presidents.html').read_text(); print(len(h)); assert 'US Presidents' in h; print('title present')"`
Expected: prints a large length and `title present`.

- [ ] **Step 4: Run the whole test suite**

Run: `python -m pytest -v`
Expected: all tests in `tests/` PASS.

- [ ] **Step 5: Verify in a browser (manual)**

Open `presidents.html` in a browser. Confirm: cards show portraits, and the facet panel lets you sort/group/filter by party, birth_state, age_at_inauguration, date_of_birth, number, etc. Note anything off.

- [ ] **Step 6: Commit the finished viewer**

```bash
git add presidents.html
git commit -m "feat: build US Presidents PivotViewer output"
```

---

## Self-Review Notes

- **Spec coverage:** data model (Task 2), scraping (Task 3), build/single-file (Task 4), verification + BuildSummary (Task 5), README/requirements (Task 1), Cleveland/Trump one-row decision (Global Constraints + Task 2 data). All spec sections map to a task.
- **Decision recorded:** the spec named only Cleveland; this plan extends the same one-row treatment to Trump (45th & 47th) for consistency, with the `terms` column preserving the non-consecutive detail. Flag to the user at execution start in case they prefer two rows.
- **Type consistency:** `load_df`, `validate`, `build_viewer`, `FACETS`, `CARD_FIELDS`, `CSV` are referenced identically across `build.py` and `tests/test_build.py`; `parse_portraits`, `lastname_slug`, `match_row_to_stem`, `main` identical across `scrape_images.py` and `tests/test_scrape.py`.
