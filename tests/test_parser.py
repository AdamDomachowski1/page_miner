"""Tests for HTML cleaning, Markdown conversion and link extraction."""

from page_miner.parser import parse_page

PAGE = """
<html>
<head><script>evil()</script><style>.x{}</style></head>
<body>
  <nav><a href="/hidden-in-nav">Nav link</a></nav>
  <div class="cookie-banner">We use cookies!</div>
  <main>
    <h1>Title</h1>
    <p>Hello world.</p>
    <a href="/about">About</a>
    <a href="/about/">About again</a>
    <a href="/about#team">About team</a>
    <a href="https://other.example.com/">External</a>
    <a href="/photo.jpg">Image</a>
    <a href="mailto:x@example.com">Mail</a>
    <img src="data:image/gif;base64,AAAA" data-src="https://example.com/real.jpg">
    <img src="data:image/gif;base64,BBBB">
  </main>
</body>
</html>
"""


def test_markdown_strips_noise_and_banners():
    md = parse_page(PAGE).markdown
    assert "Title" in md
    assert "Hello world." in md
    assert "evil()" not in md
    assert "cookies" not in md
    assert "Nav link" not in md


def test_lazy_image_swapped_and_placeholder_dropped():
    md = parse_page(PAGE).markdown
    assert "https://example.com/real.jpg" in md
    assert "base64" not in md


def test_links_require_base_url():
    assert parse_page(PAGE).links == []


def test_layout_table_flattened_to_paragraphs():
    html = """
    <body><main><table><tr>
      <td><p>Left column story.</p></td>
      <td><p>Right column story.</p></td>
    </tr></table></main></body>
    """
    md = parse_page(html).markdown
    assert "Left column story." in md
    assert "Right column story." in md
    assert "|" not in md  # no markdown table markup


def test_data_table_is_preserved():
    html = """
    <body><main><table>
      <tr><th>Name</th><th>Price</th></tr>
      <tr><td>Room</td><td>100</td></tr>
    </table></main></body>
    """
    md = parse_page(html).markdown
    assert "| Name | Price |" in md


def test_invisible_chars_and_artifact_lines_removed():
    html = "<body><main><p>a​b</p><p>›</p><p>ok</p></main></body>"
    md = parse_page(html).markdown
    assert "ab" in md
    assert "​" not in md
    assert "›" not in md
    assert "ok" in md


def test_links_same_domain_deduplicated():
    links = parse_page(PAGE, base_url="https://example.com/start").links
    # nav links are collected too (extraction runs before cleaning),
    # /about variants collapse to one, external/mailto/assets are dropped
    assert links == [
        "https://example.com/hidden-in-nav",
        "https://example.com/about",
    ]
