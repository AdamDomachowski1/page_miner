"""Tests for filenames and the combined crawl document."""

from datetime import date

from page_miner.crawler import Page
from page_miner.output import combine_pages, crawl_filename, page_filename, save


def test_page_filename_is_safe_and_dated():
    name = page_filename("https://example.com/some/path?q=1")
    assert name == f"example_com_some_path_{date.today()}.md"


def test_crawl_filename_uses_host_only():
    assert crawl_filename("https://example.com/deep/path") == f"example_com_crawl_{date.today()}.md"


def test_combine_pages_has_toc_and_sections():
    pages = [
        Page(url="https://example.com", depth=0, content="Home content"),
        Page(url="https://example.com/about", depth=1, content=""),
    ]
    doc = combine_pages(pages, "https://example.com")
    assert "# Crawl of example.com" in doc
    assert "Pages: 2" in doc
    assert "1. https://example.com" in doc
    assert "# [1] https://example.com" in doc
    assert "Home content" in doc
    assert "_(empty page)_" in doc  # empty pages get a placeholder


def test_boilerplate_kept_on_first_page_only():
    menu = "* HOME\n* About\n* Contact"
    footer = "### Phone\n123 456 789"
    pages = [
        Page(url=f"https://example.com/{i}", depth=1,
             content=f"{menu}\n\nUnique content {i}\n\n{footer}")
        for i in range(5)
    ]
    doc = combine_pages(pages, "https://example.com")
    assert doc.count(menu) == 1    # kept once, on the first page
    assert doc.count(footer) == 1
    for i in range(5):
        assert f"Unique content {i}" in doc  # real content untouched


def test_no_boilerplate_stripping_for_tiny_crawls():
    pages = [
        Page(url="https://example.com/1", depth=0, content="Same\n\nA"),
        Page(url="https://example.com/2", depth=1, content="Same\n\nB"),
    ]
    doc = combine_pages(pages, "https://example.com")
    assert doc.count("Same") == 2  # too few pages to judge what's boilerplate


def test_save_creates_directory(tmp_path):
    path = save("hello", tmp_path / "nested" / "out", "file.md")
    assert path.read_text() == "hello"
