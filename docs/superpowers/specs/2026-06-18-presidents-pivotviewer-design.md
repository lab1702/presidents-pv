# US Presidents PivotViewer — Design

**Date:** 2026-06-18
**Status:** Approved (design)

## Goal

A repeatable Python pipeline that builds a portable, single-file `presidents.html`
PivotViewer of all US presidents using the `pview` package, letting users sort,
group, and filter by a rich set of facets (party, birth state, age at inauguration,
dates, presidency order, lifespan, etc.).

## Background

`pview` (https://github.com/lab1702/pview, installed editable from `/home/lab/tmp/pview`)
is a build-time generator that turns a pandas DataFrame into a static web bundle.
Key API:

```python
from pview import build
build(
    df,                       # one row per item
    name_col="name",          # required; the card title (text facet)
    image_col="image",        # local path or http(s) URL per row; failed images fall back to a generated text card
    card_fields=[...],        # columns rendered on each card face
    facets={...},             # override column classification: {"col": "category|numeric|date|text"}
    title="US Presidents",
    out_dir="...",            # required
    single_file=True,         # emit one portable index.html with base64-inlined assets
)
```

- Auto-classification: datetime → `date`; numeric → `numeric`; ≤50 unique values → `category`; else `text`. `image_col` is excluded from faceting.
- Python 3.11+ (3.14 available locally). Deps: pandas, pillow, httpx.
- Remote image fetching validates against private IP ranges, caps downloads at 64 MiB, rejects >~50 MP images.

## Decisions (from brainstorming)

- **Data source:** Hand-curate the factual dataset from well-established history; scrape **only portrait images** from presidency.ucsb.edu.
- **Attributes:** Core five (name, years in office, birth state, age at first inauguration, DOB) **plus** political party, presidency number/order, and lifespan facets (date of death, age at death, living status).
- **Deliverable:** Repeatable script + committed data file; pview emits a **single-file** portable `presidents.html`.
- **Coverage:** All presidencies through the current (47th). **Grover Cleveland** = one row (number 22, non-consecutive terms noted), not two, to avoid a duplicate card.

## Project structure

```
presidents_pv/
├── data/presidents.csv        # curated, reviewable dataset (one row per president)
├── images/                    # scraped portraits, e.g. 01_washington.jpg
├── scrape_images.py           # downloads portraits from presidency.ucsb.edu → images/
├── build.py                   # loads CSV, calls pview.build(single_file=True)
├── presidents.html            # OUTPUT: portable single-file viewer
├── README.md                  # how to re-run the pipeline
└── requirements.txt
```

## Data model — `data/presidents.csv`

| Column | pview facet type | Notes |
|---|---|---|
| `number` | numeric | Presidency ordinal (1–47); chronological sort |
| `name` | text | `name_col`; card title |
| `party` | category | Democrat, Republican, Whig, Federalist, Democratic-Republican, National Union, etc. |
| `term_start` | numeric (year) | Inauguration year |
| `term_end` | numeric (year) | Term end year; blank for the current president |
| `years_served` | numeric | Whole/fractional years in office (convenience facet) |
| `birth_state` | category | State (or territory/country) of birth |
| `date_of_birth` | date | ISO `YYYY-MM-DD` |
| `age_at_inauguration` | numeric | Age at **first** inauguration |
| `date_of_death` | date | Blank if living |
| `age_at_death` | numeric | Blank if living |
| `living` | category | `Yes` / `No` |
| `image` | (image_col) | Relative path into `images/`, e.g. `images/01_washington.jpg` |

Facets are passed explicitly to `pview.build` to lock classification
(`party`, `birth_state`, `living` → `category`; date columns → `date`; numeric → `numeric`).

## Components

### 1. `data/presidents.csv` (curated)
- One row per presidency, ordered by `number`.
- Values cross-checked against well-established history. Edge cases:
  - **Grover Cleveland:** single row, `number=22`, note non-consecutive terms.
  - **Current president (47th):** blank `term_end`, `living=Yes`, blank death fields.
  - Birth states reflect the state/territory as it is conventionally attributed (e.g., Virginia for early presidents).

### 2. `scrape_images.py`
- Fetches the presidency.ucsb.edu `/presidents` index, parses each portrait URL, downloads to `images/NN_lastname.jpg`.
- **Polite:** realistic User-Agent, small delay between requests.
- **Idempotent:** skips files that already exist (safe to re-run).
- **Tolerant:** a failed/missing portrait is logged and skipped; the corresponding viewer card falls back to pview's generated text card. Never aborts the whole run.
- Filenames in `images/` align with the `image` column in the CSV.

### 3. `build.py`
- Reads `data/presidents.csv` with pandas (dtypes: dates parsed, numerics coerced, blanks → NaN/empty).
- Calls `build(df, name_col="name", image_col="image", card_fields=["name","party","term_start"], facets={...}, title="US Presidents", out_dir=..., single_file=True)`.
- Prints the returned `BuildSummary` (n_items, n_generated, n_image_errors, n_atlases).
- Resulting portable HTML is written/copied to `presidents.html`.

### 4. `README.md` + `requirements.txt`
- README documents: install deps, run `scrape_images.py`, run `build.py`, open `presidents.html`.
- `requirements.txt` pins `pview` (or references the local editable install), `pandas`, `pillow`, `httpx`, and the scraper's HTML-parsing dep.

## Data flow

```
presidency.ucsb.edu/presidents ──scrape_images.py──▶ images/NN_*.jpg
data/presidents.csv (curated) ──┐
                                ├──build.py──▶ pview.build(single_file=True) ──▶ presidents.html
images/ ────────────────────────┘
```

## Error handling

- **Scraping:** network/parse errors per-president are caught and logged; the build still succeeds with text-card fallbacks. Re-running fills gaps without re-downloading existing images.
- **Build:** pview never aborts on a bad image. `build.py` surfaces the `BuildSummary` so image-error counts are visible.
- **Data:** `build.py` validates the CSV has the expected columns and a unique `number`/`name` before building; fails fast with a clear message otherwise.

## Verification

- After build, confirm `presidents.html` exists and is non-trivial in size (single-file inlines images, so it should be sizable).
- Report `BuildSummary` counts; investigate if `n_image_errors` is high.
- Spot-check the dataset row count (~47) and a few known values (e.g., Washington age 57, Theodore Roosevelt youngest at 42).

## Out of scope (YAGNI)

- Scraping structured biographical data from the site (we curate it instead).
- Two separate rows for Cleveland's non-consecutive terms.
- A live web server or hosting; the deliverable is a portable HTML file.
- Automated data-accuracy tests beyond column/uniqueness validation and manual spot-checks.
