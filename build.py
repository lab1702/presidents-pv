"""Build the portable presidents.html PivotViewer from data/presidents.csv."""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from pview import build as pview_build

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "data" / "presidents.csv"

DATE_COLS = ["date_of_birth", "date_of_death"]
INT_COLS = ["number", "term_start", "term_end", "age_at_inauguration", "age_at_death"]
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
    for col in INT_COLS:
        df[col] = df[col].astype("Int64")
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
