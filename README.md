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
