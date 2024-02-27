import typer
import os
import genanki
import json
from datetime import datetime, timedelta
from typing import List

app = typer.Typer()


def parse_json(file_path: str, start_date=None, end_date=None):
    # Logic to parse JSON file and extract data based on date filters
    pass


def create_flashcards(data, output_file):
    # Logic to create flashcards using genanki and save to output_file
    pass


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
        print(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file: {file_path}")
        return []


# Example usage
file_path = "selkouutiset-scrape-cleaned/2023/10/26/_request.fi.en.json"
request_texts = parse_request_json(file_path)


def parse_response_json(file_path: str) -> List[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            translations = data.get("data", {}).get("translations", [])
            return [item.get("translatedText", "") for item in translations]
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file: {file_path}")
        return []


# Example usage
file_path = "selkouutiset-scrape-cleaned/2023/10/26/_response.fi.en.json"
response_texts = parse_response_json(file_path)


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
        raise typer.Exit(f"No data found for date: {date}")

    # Create flashcards (assuming create_flashcards can handle the format of translation_pairs)
    create_flashcards(translation_pairs, output)

    typer.echo(f"Flashcards generated for {date} in {output}")


def generate_flashcards(start_date, end_date, output):
    start = datetime.strptime(start_date, "%Y.%m.%d")
    end = datetime.strptime(end_date, "%Y.%m.%d")
    current_date = start

    while current_date <= end:
        generate_flashcards_for_date(current_date.strftime("%Y.%m.%d"), output)
        current_date += timedelta(days=1)


@app.command()
def today(output: str = typer.Option("cards.anki", help="Output Anki file name")):
    today_date = datetime.now().strftime("%Y.%m.%d")
    generate_flashcards(today_date, today_date, output)


@app.command()
def everything(output: str = typer.Option("cards.anki", help="Output Anki file name")):
    # Placeholder start_date and end_date. Replace these with actual logic to determine dates.
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
    output: str = typer.Option("cards.anki", help="Output Anki file name"),
):
    generate_flashcards(start_date, end_date, output)


if __name__ == "__main__":
    app()
