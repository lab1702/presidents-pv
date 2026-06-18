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
