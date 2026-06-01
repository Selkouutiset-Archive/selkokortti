import json
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

import colorlog
import genanki
import typer

from . import __version__
from .data import resolve_data_dir

APP_HELP = """Generate Anki flashcards from Andrew's Selkouutiset Archive (Finnish easy-news).

The default direction is Finnish -> English. Use -d en-fi for English -> Finnish
production practice, or -d both for bidirectional cards (one note, two cards).
The news dataset is downloaded and kept up to date for you automatically.
"""

APP_EPILOG = """Examples:
  selkokortti latest 7                       last 7 days of articles
  selkokortti range 2025.06.20 2025.06.23    an inclusive date range
  selkokortti range 2025.06.20 2025.06.23 -d both    bidirectional cards
  selkokortti today -d en-fi                 today's article, English -> Finnish
  selkokortti info                           show cache location + available dates
"""

app = typer.Typer(help=APP_HELP, epilog=APP_EPILOG, no_args_is_help=True)

# Configure logger
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)s:%(name)s:%(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
)
logger = colorlog.getLogger("selkokortti")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# There is no inherent meaning in these numbers.
# They just need to be stable so Anki can identify the models/deck across runs.
MODEL_ID_FI_EN = 1178313288
MODEL_ID_EN_FI = 1178313289
MODEL_ID_BOTH = 1178313290
DECK_ID = 1813209776


class Direction(str, Enum):
    fi_en = "fi-en"
    en_fi = "en-fi"
    both = "both"


# --- Card templates -------------------------------------------------------
# A small MVC-in-genanki: each template is a {{field}}-driven HTML view.

_FI_FRONT = """
<div class="deck">
{{Deck}}
</div>
<div class="card">
    <div class="front-content" id="front-content">
       {{Finnish}}
    </div>
    <div class="back-content">
    </div>
</div>
"""

_FI_BACK = """
<div class="deck">
{{Deck}}
</div>
<div class="card">
    <div class="front-content" id="front-content">
       {{Finnish}}
    </div>
    <div class="back-content">
       {{English}}
    </div>
</div>
<hr />
<aside>
    <p>Proudly brought to you by <a href="https://hiandrewquinn.github.io/selkouutiset-archive/">Andrew's Selkouutiset Archive</a>.</p>
    <p>Find this useful? <a href="https://www.linkedin.com/in/heiandrewquinn/">Add Andrew on LinkedIn</a>!</p>
    <p>Spotted a bug? <a href="https://github.com/Selkouutiset-Archive/selkokortti/issues">Let us know on Github!</a></p>
</aside>
"""

_EN_FRONT = """
<div class="deck">
{{Deck}}
</div>
<div class="card">
    <div class="front-content" id="front-content">
       {{English}}
    </div>
    <div class="back-content">
    </div>
</div>
"""

_EN_BACK = """
<div class="deck">
{{Deck}}
</div>
<div class="card">
    <div class="front-content" id="front-content">
       {{English}}
    </div>
    <div class="back-content">
       {{Finnish}}
    </div>
</div>
<hr />
<aside>
    <p>Proudly brought to you by <a href="https://hiandrewquinn.github.io/selkouutiset-archive/">Andrew's Selkouutiset Archive</a>.</p>
    <p>Find this useful? <a href="https://www.linkedin.com/in/heiandrewquinn/">Add Andrew on LinkedIn</a>!</p>
    <p>Spotted a bug? <a href="https://github.com/Selkouutiset-Archive/selkokortti/issues">Let us know on Github!</a></p>
</aside>
"""

selko_css = """
/* Style for the card */
.card {
    font-size: 36px;
    text-align: center;
}

/* Style for the deck container */
.deck {
    font-size: 50%;
    padding: 20px;
}

/* Style for the front content */
.front-content {
    padding: 20px;
    color: darkred; /* Dark red color for Light mode */
}

/* Style for the back content */
.back-content {
    padding: 20px;
    color: darkblue; /* Dark blue color for Light mode */
}

/* Adjustments for Dark mode */
.card.nightMode .front-content {
    color: #FFA07A; /* Light red color for Dark mode */
}

.card.nightMode .back-content {
    color: #ADD8E6; /* Light blue color for Dark mode */
}

aside {
    font-family: serif;
    font-size: 50%;
}

/* Media query for smaller screens */
@media only screen and (max-width: 600px) {
    .card {
        font-size: 24px; /* Reduce font size to 24px for small screens */
    }
}
"""

_FIELDS = [{"name": "Deck"}, {"name": "Finnish"}, {"name": "English"}]

_TEMPLATE_FI_EN = {"name": "Finnish to English", "qfmt": _FI_FRONT, "afmt": _FI_BACK}
_TEMPLATE_EN_FI = {"name": "English to Finnish", "qfmt": _EN_FRONT, "afmt": _EN_BACK}

MODELS = {
    Direction.fi_en: genanki.Model(
        MODEL_ID_FI_EN,
        "Selko",
        fields=_FIELDS,
        templates=[_TEMPLATE_FI_EN],
        css=selko_css,
    ),
    Direction.en_fi: genanki.Model(
        MODEL_ID_EN_FI,
        "Selko (English to Finnish)",
        fields=_FIELDS,
        templates=[_TEMPLATE_EN_FI],
        css=selko_css,
    ),
    Direction.both: genanki.Model(
        MODEL_ID_BOTH,
        "Selko (bidirectional)",
        fields=_FIELDS,
        templates=[_TEMPLATE_FI_EN, _TEMPLATE_EN_FI],
        css=selko_css,
    ),
}


# --- Data parsing ---------------------------------------------------------

def parse_request_json(file_path: str) -> List[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("q", [])
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON in file: {file_path}")
        return []


def parse_response_json(file_path: str) -> List[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            translations = data.get("data", {}).get("translations", [])
            return [item.get("translatedText", "") for item in translations]
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON in file: {file_path}")
        return []


def zip_translations(
    original_texts: List[str], translated_texts: List[str]
) -> List[tuple]:
    if len(original_texts) != len(translated_texts):
        raise ValueError(
            "The lengths of the original and translated text lists do not match."
        )

    return list(zip(original_texts, translated_texts))


def filter_translations(paired_texts: List[tuple]) -> List[tuple]:
    filtered_texts = []

    for original, translation in paired_texts:
        # Skip empty pairs
        if original == "" and translation == "":
            continue

        # Skip pairs starting with '![', indicating Markdown images
        if original.startswith("![") or translation.startswith("!["):
            continue

        filtered_texts.append((original, translation))

    return filtered_texts


def process_translations_for_date(data_dir: Path, date: str) -> List[tuple]:
    # Construct file paths
    year, month, day = date.split(".")
    base_path = Path(data_dir) / year / month / day
    request_file_path = base_path / "_request.fi.en.json"
    response_file_path = base_path / "_response.fi.en.json"

    # Parse JSON files
    request_texts = parse_request_json(str(request_file_path))
    response_texts = parse_response_json(str(response_file_path))

    # Zip and filter translations
    zipped_texts = zip_translations(request_texts, response_texts)
    filtered_texts = filter_translations(zipped_texts)

    return filtered_texts


def find_date_range(directory_path: Path) -> Tuple[str, str]:
    earliest_date = datetime.max
    latest_date = datetime.min

    for root, dirs, files in os.walk(str(directory_path)):
        parts = root.split(os.sep)
        if len(parts) >= 3:
            try:
                year = int(parts[-3])
                month = int(parts[-2])
                day = int(parts[-1])
                current_date = datetime(year, month, day)

                if current_date < earliest_date:
                    earliest_date = current_date
                if current_date > latest_date:
                    latest_date = current_date
            except ValueError:
                continue

    if earliest_date == datetime.max:
        raise RuntimeError(f"No dated entries found under {directory_path}")

    return earliest_date.strftime("%Y.%m.%d"), latest_date.strftime("%Y.%m.%d")


def available_dates(directory_path: Path) -> List[str]:
    """Return every YYYY.MM.DD that has an article, sorted ascending."""
    dates = []
    for root, dirs, files in os.walk(str(directory_path)):
        parts = root.split(os.sep)
        if len(parts) >= 3:
            try:
                current = datetime(int(parts[-3]), int(parts[-2]), int(parts[-1]))
            except ValueError:
                continue
            dates.append(current.strftime("%Y.%m.%d"))
    return sorted(dates)


def date_has_article(data_dir: Path, date_str: str) -> bool:
    year, month, day = date_str.split(".")
    return (Path(data_dir) / year / month / day).is_dir()


def _latest_date_hint(data_dir: Path) -> Optional[str]:
    try:
        _, latest = find_date_range(data_dir)
    except RuntimeError:
        return None
    return latest


# --- Deck building --------------------------------------------------------

def build_deck(
    data_dir: Path,
    start_date: str,
    end_date: str,
    direction: Direction,
    deck_name: str = "Selko",
    warn_missing: bool = True,
) -> genanki.Deck:
    start = datetime.strptime(start_date, "%Y.%m.%d")
    end = datetime.strptime(end_date, "%Y.%m.%d")
    if start > end:
        raise typer.BadParameter(
            f"start date {start_date} is after end date {end_date}."
        )

    model = MODELS[direction]
    deck = genanki.Deck(DECK_ID, deck_name)

    current_date = start
    note_count = 0
    missing_count = 0
    while current_date <= end:
        date_str = current_date.strftime("%Y.%m.%d")
        if not date_has_article(data_dir, date_str):
            missing_count += 1
            if warn_missing:
                logger.warning("No article published for %s (skipped).", date_str)
            else:
                logger.debug("No article for %s (skipped).", date_str)
            current_date += timedelta(days=1)
            continue
        pairs = process_translations_for_date(data_dir, date_str)
        deck_label = f"{deck_name} :: {date_str}"
        for finnish, english in pairs:
            deck.add_note(
                genanki.Note(model=model, fields=[deck_label, finnish, english])
            )
            note_count += 1
        logger.debug("Added %d notes for %s", len(pairs), date_str)
        current_date += timedelta(days=1)

    if note_count == 0:
        logger.error(
            "No flashcards generated: no articles found for %s .. %s.",
            start_date,
            end_date,
        )
        latest = _latest_date_hint(data_dir)
        if latest:
            logger.error(
                "The most recent available date is %s — try: "
                "selkokortti range %s %s",
                latest,
                latest,
                latest,
            )
        raise typer.Exit(code=1)

    logger.info(
        "Built %d notes (%s) for %s .. %s",
        note_count,
        direction.value,
        start_date,
        end_date,
    )
    return deck


def write_deck(deck: genanki.Deck, output_file: str) -> None:
    genanki.Package(deck).write_to_file(output_file)
    logger.info("Wrote %s", output_file)


def set_logging(quiet: bool, verbose: bool):
    if quiet:
        logger.setLevel(logging.WARNING)
    elif verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


# --- Shared option helpers ------------------------------------------------

OutputOpt = typer.Option("cards.apkg", help="Output Anki file name.")
DeckNameOpt = typer.Option(
    "Selko", "--deck-name", help="Name of the generated Anki deck."
)
DirectionOpt = typer.Option(
    Direction.fi_en,
    "--direction",
    "-d",
    help="Card direction: fi-en (Finnish prompt), en-fi (English prompt), "
    "or both (one note, two linked cards).",
)
DataDirOpt = typer.Option(
    None,
    "--data-dir",
    help="Use a local checkout of selkouutiset-scrape-cleaned instead of the "
    "auto-managed cache (no network access).",
)
NoUpdateOpt = typer.Option(
    False, "--no-update", help="Do not refresh the cached dataset before building."
)
VerboseOpt = typer.Option(
    False, "--verbose", "-v", help="Print DEBUG level logs (normal level: INFO)."
)
QuietOpt = typer.Option(
    False,
    "--quiet",
    "-q",
    help="Print WARNING level logs (normal level: INFO). Overrides --verbose.",
)


# --- Commands -------------------------------------------------------------

def _version_callback(value: bool):
    if value:
        typer.echo(f"selkokortti {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the selkokortti version and exit.",
    ),
):
    """Generate Anki flashcards from Andrew's Selkouutiset Archive."""


@app.command(epilog="Example: selkokortti today -d both")
def today(
    output: str = OutputOpt,
    direction: Direction = DirectionOpt,
    deck_name: str = DeckNameOpt,
    data_dir: Optional[str] = DataDirOpt,
    no_update: bool = NoUpdateOpt,
    verbose: bool = VerboseOpt,
    quiet: bool = QuietOpt,
):
    """Generate flashcards for today's date."""
    set_logging(quiet, verbose)
    resolved = resolve_data_dir(data_dir, no_update)
    today_date = datetime.now().strftime("%Y.%m.%d")
    deck = build_deck(resolved, today_date, today_date, direction, deck_name)
    write_deck(deck, output)


@app.command(epilog="Example: selkokortti everything --output all.apkg")
def everything(
    output: str = OutputOpt,
    direction: Direction = DirectionOpt,
    deck_name: str = DeckNameOpt,
    data_dir: Optional[str] = DataDirOpt,
    no_update: bool = NoUpdateOpt,
    verbose: bool = VerboseOpt,
    quiet: bool = QuietOpt,
):
    """Generate flashcards for every available date."""
    set_logging(quiet, verbose)
    resolved = resolve_data_dir(data_dir, no_update)
    start_date, end_date = find_date_range(resolved)
    # Gaps (weekends, holidays) across the full archive are expected, so don't
    # warn per missing date here.
    deck = build_deck(
        resolved, start_date, end_date, direction, deck_name, warn_missing=False
    )
    write_deck(deck, output)


@app.command(epilog="Example: selkokortti range 2025.06.20 2025.06.23 -d both")
def range(
    start_date: str = typer.Argument(
        ..., formats=["%Y.%m.%d"], help="Start date in yyyy.mm.dd format"
    ),
    end_date: str = typer.Argument(
        ..., formats=["%Y.%m.%d"], help="End date in yyyy.mm.dd format"
    ),
    output: str = OutputOpt,
    direction: Direction = DirectionOpt,
    deck_name: str = DeckNameOpt,
    data_dir: Optional[str] = DataDirOpt,
    no_update: bool = NoUpdateOpt,
    verbose: bool = VerboseOpt,
    quiet: bool = QuietOpt,
):
    """Generate flashcards for an inclusive date range."""
    set_logging(quiet, verbose)
    resolved = resolve_data_dir(data_dir, no_update)
    deck = build_deck(resolved, start_date, end_date, direction, deck_name)
    write_deck(deck, output)


@app.command(epilog="Example: selkokortti latest 7 -d both")
def latest(
    count: int = typer.Argument(
        7, min=1, help="Number of most recent available dates to include."
    ),
    output: str = OutputOpt,
    direction: Direction = DirectionOpt,
    deck_name: str = DeckNameOpt,
    data_dir: Optional[str] = DataDirOpt,
    no_update: bool = NoUpdateOpt,
    verbose: bool = VerboseOpt,
    quiet: bool = QuietOpt,
):
    """Generate flashcards for the N most recent available dates."""
    set_logging(quiet, verbose)
    resolved = resolve_data_dir(data_dir, no_update)
    dates = available_dates(resolved)
    if not dates:
        logger.error("No articles found under %s.", resolved)
        raise typer.Exit(code=1)
    chosen = dates[-count:]
    # chosen are all existing dates; gaps within the window are expected.
    deck = build_deck(
        resolved, chosen[0], chosen[-1], direction, deck_name, warn_missing=False
    )
    write_deck(deck, output)


@app.command()
def info(
    data_dir: Optional[str] = DataDirOpt,
    no_update: bool = NoUpdateOpt,
    verbose: bool = VerboseOpt,
    quiet: bool = QuietOpt,
):
    """Show the dataset cache location and the available date range."""
    set_logging(quiet, verbose)
    resolved = resolve_data_dir(data_dir, no_update)
    typer.echo(f"selkokortti {__version__}")
    typer.echo(f"Data directory: {resolved}")
    dates = available_dates(resolved)
    if not dates:
        typer.echo("Available dates: none (dataset is empty)")
        return
    typer.echo(f"Available dates: {dates[0]} .. {dates[-1]} ({len(dates)} days)")


if __name__ == "__main__":
    app()
