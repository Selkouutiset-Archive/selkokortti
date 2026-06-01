import pytest
import typer

from selkokortti.cli import (
    Direction,
    _parse_direction,
    available_dates,
    date_has_article,
    filter_translations,
    find_date_range,
    parse_request_json,
    parse_response_json,
    process_translations_for_date,
    render_text,
    zip_translations,
)

DATE = "2025.01.02"


def test_parse_request_json(data_dir):
    q = parse_request_json(str(data_dir / "2025/01/02/_request.fi.en.json"))
    assert q[0].startswith("#")
    assert "Tämä on ensimmäinen lause." in q


def test_parse_response_json(data_dir):
    t = parse_response_json(str(data_dir / "2025/01/02/_response.fi.en.json"))
    assert "This is the first sentence." in t


def test_parse_missing_file_returns_empty():
    assert parse_request_json("/nope/missing.json") == []
    assert parse_response_json("/nope/missing.json") == []


def test_zip_translations_length_mismatch():
    with pytest.raises(ValueError):
        zip_translations(["a", "b"], ["x"])


def test_filter_drops_headers_teaser_images_empties(data_dir):
    pairs = process_translations_for_date(data_dir, DATE)
    finnish = [fi for fi, _ in pairs]
    # Real sentences kept (incl. the duplicate, which build_deck dedups later).
    assert "Tämä on ensimmäinen lause." in finnish
    assert finnish.count("Tämä on toistettu lause.") == 2
    assert "Tom & Jerry **lihavoitu**." in finnish
    # Headers, teaser, empties, and images dropped.
    assert not any(f.strip().startswith("#") for f in finnish)
    assert "Aihe yksi. Aihe kaksi." not in finnish
    assert not any(f.startswith("![") for f in finnish)
    assert "" not in finnish


def test_filter_keeps_content_when_no_section_header():
    # No '##' header => don't over-filter; keep the plain sentence.
    pairs = [("Pelkkä lause.", "Just a sentence.")]
    assert filter_translations(pairs) == pairs


def test_render_text_escapes_and_converts_markdown():
    assert render_text("Tom & Jerry **bold**.") == "Tom &amp; Jerry <b>bold</b>."
    assert render_text("a <b> c") == "a &lt;b&gt; c"
    assert render_text("see [here](https://x.io)") == 'see <a href="https://x.io">here</a>'
    assert render_text("_kissa_") == "<i>kissa</i>"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("fi-en", Direction.fi_en),
        ("finnish-english", Direction.fi_en),
        ("en-fi", Direction.en_fi),
        ("english-finnish", Direction.en_fi),
        ("both", Direction.both),
        ("bidirectional", Direction.both),
        ("BI", Direction.both),
        ("  Both  ", Direction.both),
    ],
)
def test_parse_direction_aliases(value, expected):
    assert _parse_direction(value) is expected


def test_parse_direction_none_passthrough():
    assert _parse_direction(None) is None


def test_parse_direction_invalid_raises():
    with pytest.raises(typer.BadParameter):
        _parse_direction("sideways")


def test_date_helpers(data_dir):
    assert date_has_article(data_dir, DATE) is True
    assert date_has_article(data_dir, "2025.01.03") is False
    assert available_dates(data_dir) == [DATE]
    assert find_date_range(data_dir) == (DATE, DATE)
