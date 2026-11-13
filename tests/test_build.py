import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

from ho.build import main

ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
PAGES = ["index.html", "phrasebook/index.html", "katakana/index.html", "lessons/03/index.html",
         "kanji/index.html", "kanji/65e5/index.html", "kanji/drill/index.html", "reading/index.html",
         "reading/03-depato/index.html"]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("build") / "site"
    assert main(["--out", str(out)]) == 0
    return out


def test_pages_exist(site):
    for rel in [*PAGES, "static/css/site.css", "static/js/phrasebook.js", ".nojekyll"]:
        assert (site / rel).is_file(), rel


@pytest.mark.parametrize("page", PAGES)
def test_links_are_relative_and_resolve(site, page):
    html = (site / page).read_text()
    for tag, url in re.findall(r'<(\w+)[^>]*?(?:href|src)="([^"]*)"', html):
        parsed = urlparse(url)
        if parsed.scheme:
            # Outbound links may go anywhere; anything the page loads only from the font hosts.
            assert parsed.scheme == "https", url
            assert tag == "a" or parsed.hostname in ALLOWED_HOSTS, url
            continue
        assert not url.startswith("/"), url
        target = site / page
        if parsed.path:
            target = (site / page).parent / parsed.path
            if parsed.path.endswith("/"):
                target = target / "index.html"
        assert target.resolve().is_file(), f"{page}: {url}"
        if parsed.fragment:
            assert f'id="{parsed.fragment}"' in target.read_text(), f"{page}: {url}"


def data(site, page):
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', (site / page).read_text(), re.S)
    return json.loads(m.group(1))


def test_embedded_data(site):
    assert len(data(site, "phrasebook/index.html")["phrases"]) == 545
    words = data(site, "katakana/index.html")
    assert len(words) == 198
    assert {"exact", "near_long", "typed", "macron", "ru", "uk"} <= set(words[0])


def test_deterministic(site, tmp_path):
    again = tmp_path / "again"
    assert main(["--out", str(again)]) == 0
    files = sorted(p.relative_to(site) for p in site.rglob("*") if p.is_file())
    assert files == sorted(p.relative_to(again) for p in again.rglob("*") if p.is_file())
    for rel in files:
        assert (site / rel).read_bytes() == (again / rel).read_bytes(), rel


def test_refuses_to_clear_foreign_dir(tmp_path):
    (tmp_path / "keep.txt").write_text("mine")
    with pytest.raises(SystemExit):
        main(["--out", str(tmp_path)])
    assert (tmp_path / "keep.txt").exists()
