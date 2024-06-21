import typer
import os
import genanki
import json
import logging
from datetime import datetime, timedelta
from typing import List
import colorlog

app = typer.Typer()

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
logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# There is no inherent meaning in these numbers.
# It's just needed for Anki to identify the model.
MODEL_ID = 1178313288
DECK_ID = 1813209776

# The fun thing about genanki is it's like a tiny MVC framework all in one.
selko_front_view = """
<div class="deck">
{{Deck}}
</div>
<div class="card">
    <div class="front-content" id="front-content">
       {{Finnish}}
       <!-- <div id="shuffled-sentence"></div> -->
    </div>
    <div class="back-content">
    </div>
</div>
"""

selko_back_view = """
<div class="deck">
{{Deck}}
</div>
<div class="card">
    <div class="front-content" id="front-content">
       {{Finnish}}
       <!-- <div id="shuffled-sentence"></div> -->
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
.card.nightMode {
    .front-content {
        color: #FFA07A; /* Light red color for Dark mode */
    }

    .back-content {
        color: #ADD8E6; /* Light blue color for Dark mode */
    }
}

aside {
    font-size:80%;
}
"""

model = genanki.Model(
    MODEL_ID,
    "Selko",
    fields=[
        {"name": "Finnish"},
        {"name": "English"},
    ],
    templates=[
        {
            "name": "Finnish to English",
            "qfmt": selko_front_view,
            "afmt": selko_back_view,
        },
    ],
    css=selko_css,
)

deck = genanki.Deck(DECK_ID, "Selko")


def parse_json(file_path: str, start_date=None, end_date=None):
    # Logic to parse JSON file and extract data based on date filters
    pass


def create_deck(date=None, output_file="cards.apkg"):
    try:
        genanki.Package(deck).write_to_file(output_file)
    except:
        logging.error(f"Could not add {date} to {output_file}!")
    return


def create_deck_for_date(date):
    yyyy, mm, dd = date.split(".")
    return create_deck(f"Selko::{yyyy}::{mm}::{dd}")


def add_flashcards_to_deck(data, output_file):
    # Logic to create flashcards using genanki and save to output_file
    for finnish, english in data:
        note = genanki.Note(
            model=model,
            fields=[finnish, english],
        )
        deck.add_note(note)
        logger.debug(f"Created card for date: {finnish} - {english}")
    return


def find_date_range(directory_path):
    earliest_date = datetime.max
    latest_date = datetime.min

    for root, dirs, files in os.walk(directory_path):
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

    # Format dates as 'yyyy.mm.dd'
    earliest_str = earliest_date.strftime("%Y.%m.%d")
    latest_str = latest_date.strftime("%Y.%m.%d")

    return earliest_str, latest_str


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


def process_translations_for_date(date: str) -> List[tuple]:
    # Construct file paths
    year, month, day = date.split(".")
    base_path = f"selkouutiset-scrape-cleaned/{year}/{month}/{day}"
    request_file_path = f"{base_path}/_request.fi.en.json"
    response_file_path = f"{base_path}/_response.fi.en.json"

    # Parse JSON files
    request_texts = parse_request_json(request_file_path)
    response_texts = parse_response_json(response_file_path)

    # Zip and filter translations
    zipped_texts = zip_translations(request_texts, response_texts)
    filtered_texts = filter_translations(zipped_texts)

    return filtered_texts


def generate_flashcards_for_date(date, output):
    # Process translations for the given date
    translation_pairs = process_translations_for_date(date)

    # Check if there are translation pairs to process
    if not translation_pairs:
        logger.warning(f"No data found for date: {date}")
        raise typer.Exit(f"No data found for date: {date}")

    # Create flashcards (assuming add_flashcards_to_deck can handle the format of translation_pairs)
    add_flashcards_to_deck(translation_pairs, output)

    logger.info(f"Flashcards generated for {date} in {output}")


def generate_flashcards(start_date, end_date, output):
    start = datetime.strptime(start_date, "%Y.%m.%d")
    end = datetime.strptime(end_date, "%Y.%m.%d")
    current_date = start

    while current_date <= end:
        generate_flashcards_for_date(current_date.strftime("%Y.%m.%d"), output)
        create_deck_for_date(current_date.strftime("%Y.%m.%d"))
        current_date += timedelta(days=1)

    create_deck(output)


def set_logging(quiet: bool, verbose: bool):
    if quiet:
        logger.setLevel(logging.WARNING)
    elif verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


@app.command()
def today(
    output: str = typer.Option("cards.apkg", help="Output Anki file name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print DEBUG level logs (normal level: INFO)."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Print WARNING level logs (normal level: INFO). Overrides --verbose.")
):
    set_logging(verbose)
    today_date = datetime.now().strftime("%Y.%m.%d")
    generate_flashcards(today_date, today_date, output)

@app.command()
def everything(
    output: str = typer.Option("cards.apkg", help="Output Anki file name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print DEBUG level logs (normal level: INFO)."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Print WARNING level logs (normal level: INFO). Overrides --verbose.")
):
    set_logging(verbose)
    start_date, end_date = find_date_range("selkouutiset-scrape-cleaned")
    generate_flashcards(start_date, end_date, output)

@app.command()
def range(
    start_date: str = typer.Argument(
        ..., formats=["%Y.%m.%d"], help="Start date in yyyy.mm.dd format"
    ),
    end_date: str = typer.Argument(
        ..., formats=["%Y.%m.%d"], help="End date in yyyy.mm.dd format"
    ),
    output: str = typer.Option("cards.apkg", help="Output Anki file name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print DEBUG level logs (normal level: INFO)."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Print WARNING level logs (normal level: INFO). Overrides --verbose.")
):
    set_logging(quiet, verbose)
    generate_flashcards(start_date, end_date, output)

if __name__ == "__main__":
    app()
