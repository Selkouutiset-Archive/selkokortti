import pytest
import typer
from typer.testing import CliRunner

from selkokortti.cli import Direction, app, build_deck, get_model

DATE = "2025.01.02"
runner = CliRunner()


def _notes(decks):
    return [n for d in decks for n in d.notes]


def test_build_deck_dedups_and_counts(data_dir):
    decks = build_deck(data_dir, DATE, DATE, Direction.fi_en)
    notes = _notes(decks)
    # 4 filtered pairs, but the repeated sentence dedups to 3 notes.
    assert len(notes) == 3
    finnish = [n.fields[1] for n in notes]
    assert finnish.count("Tämä on toistettu lause.") == 1


def test_build_deck_one_subdeck_per_month(data_dir):
    decks = build_deck(data_dir, DATE, DATE, Direction.fi_en, deck_name="Selko")
    assert [d.name for d in decks] == ["Selko::2025::01"]


def test_build_deck_tags_and_source(data_dir):
    notes = _notes(build_deck(data_dir, DATE, DATE, Direction.fi_en))
    note = notes[0]
    assert "selko" in note.tags and "2025-01-02" in note.tags
    assert "selkouutiset-archive/2025/01/02/" in note.fields[3]


def test_build_deck_both_doubles_cards(data_dir):
    decks = build_deck(data_dir, DATE, DATE, Direction.both)
    notes = _notes(decks)
    assert len(notes) == 3
    # The 'both' model has two card templates => two cards per note.
    assert len(notes[0].cards) == 2


def test_build_deck_start_after_end_raises(data_dir):
    with pytest.raises(typer.BadParameter):
        build_deck(data_dir, "2025.01.05", "2025.01.02", Direction.fi_en)


def test_build_deck_no_articles_exits(data_dir):
    with pytest.raises(typer.Exit):
        build_deck(data_dir, "2025.01.03", "2025.01.03", Direction.fi_en)


def test_get_model_typed_toggle():
    typed = get_model(Direction.en_fi, typed=True)
    plain = get_model(Direction.en_fi, typed=False)
    assert "{{type:Finnish}}" in typed.templates[0]["qfmt"]
    assert "{{type:Finnish}}" not in plain.templates[0]["qfmt"]
    # In 'both', only the English->Finnish card is typed.
    both = get_model(Direction.both, typed=True)
    assert "{{type:Finnish}}" not in both.templates[0]["qfmt"]
    assert "{{type:Finnish}}" in both.templates[1]["qfmt"]


def test_cli_range_builds_file(data_dir, tmp_path):
    out = tmp_path / "cards.apkg"
    result = runner.invoke(
        app,
        [
            "range", DATE, DATE,
            "--data-dir", str(data_dir),
            "--no-update",
            "--output", str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists() and out.stat().st_size > 0


def test_cli_invalid_direction(data_dir, tmp_path):
    result = runner.invoke(
        app,
        ["range", DATE, DATE, "-d", "sideways", "--data-dir", str(data_dir), "--no-update"],
    )
    assert result.exit_code != 0
