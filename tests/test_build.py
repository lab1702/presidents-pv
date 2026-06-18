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
