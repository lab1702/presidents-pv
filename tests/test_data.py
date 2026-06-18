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
