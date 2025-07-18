import asyncio
import csv

import click
from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio

from tbr_deal_finder.audio_isbn import set_book_audio_isbn
from tbr_deal_finder.config import Config
from tbr_deal_finder.migrations import make_migrations
from tbr_deal_finder.seller.models import Seller
from tbr_deal_finder.book import Book, update_deals, get_deals_found_at, print_books
from tbr_deal_finder.seller.audible import Audible
from tbr_deal_finder.seller.chirp import Chirp


def _retry_books(found_books: list[Book], all_books: list[dict]) -> list[dict]:
    response = []
    found_book_set = {f'{b.title} - {b.authors}' for b in found_books}
    for book in all_books:
        if ":" not in book["Title"]:
            continue

        if f'{book["Title"]} - {book["Authors"]}' not in found_book_set:
            book["Title"] = book["Title"].split(":")[0]
            response.append(book)

    return response


async def _get_books(config, seller: Seller, books: list[dict]) -> list[Book]:
    """Get Books with limited concurrency."""
    semaphore = asyncio.Semaphore(10)
    response = []
    unresolved_books = []

    tasks = [
        seller.get_book(book["Title"], book["Authors"], config.run_time, semaphore)
        for book in books
        if book["Read Status"] == "to-read"
    ]
    results = await tqdm_asyncio.gather(*tasks, desc=f"Getting latest prices from {seller.name}")
    for book in results:
        if book.exists and book.current_price <= config.max_price and book.discount() >= config.min_discount:
            response.append(book)
        elif not book.exists:
            unresolved_books.append(book)

    if retry_books := _retry_books(response, books):
        print("Attempting to find missing books with alternate title")
        response.extend(await _get_books(config, seller, retry_books))
    elif unresolved_books:
        print()
        for book in unresolved_books:
            print(f"{book.title} by {book.authors} not found")

    return response


async def _update_deals(config: Config):
    books: list[Book] = []
    checked_deals: set[str] = set()

    def _get_deal_base(title: str, authors: str) -> str:
        return f'{title}__{authors}'

    for story_graph_export_path in config.story_graph_export_paths:
        print(f"Deals for {story_graph_export_path}")

        with open(story_graph_export_path, 'r', newline='', encoding='utf-8') as file:
            # Use csv.DictReader to get dictionaries with column headers
            tbr_books: list[dict] = [
                book for book in csv.DictReader(file)
                if _get_deal_base(book["Title"], book["Authors"]) not in checked_deals
            ]  # type: ignore

        for seller in [Audible(), Chirp()]:
            await seller.set_auth()

            print("---------------\n")
            print(f"Getting deals from {seller.name}")
            print("\n---------------")
            books.extend(await _get_books(config, seller, tbr_books))

        checked_deals.update(
            {_get_deal_base(b.title, b.authors) for b in books}
        )
        print("---------------\n")

    update_deals(books)


def _set_isbn(config: Config):
    # TODO: Enable once set_book_audio_isbn is functional

    for story_graph_export_path in config.story_graph_export_paths:
        with open(story_graph_export_path, 'r', newline='', encoding='utf-8') as file:
            # Use csv.DictReader to get dictionaries with column headers
            books: list[dict] = [book for book in csv.DictReader(file)]  # type: ignore
            if "audio_isbn" not in books[0]:
                print(f"Setting Audiobook ISBN info for {story_graph_export_path}.")
            else:
                continue

            for book in tqdm(books):
                set_book_audio_isbn(book)

        headers = list(books[0].keys())
        with open(story_graph_export_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)

            # Write header row
            writer.writeheader()

            # Write book data
            for book in books:
                # Only write fields that exist in headers
                filtered_book = {key: book.get(key, '') for key in headers}
                writer.writerow(filtered_book)


@click.command()
def main():
    """Find book deals from your StoryGraph export."""
    make_migrations()

    try:
        config = Config.load()
    except FileNotFoundError:
        click.echo("Configuration file not found. Let's set it up!")
        
        # Prompt for config values
        story_graph_export_paths = click.prompt("Enter the paths to your StoryGraph export CSV file as a comma-separated list")
        max_price = click.prompt(
            "Enter maximum price for deals (in dollars)",
            type=float,
            default=8.0
        )
        min_discount = click.prompt(
            "Enter minimum discount percentage",
            type=int,
            default=35
        )
        
        config = Config(
            story_graph_export_paths=story_graph_export_paths,
            max_price=max_price,
            min_discount=min_discount
        )
        config.save()
        click.echo("Configuration saved!")

    # TODO: Re-enable _set_isbn when set_book_audio_isbn is working
    # _set_isbn(config)
    asyncio.run(_update_deals(config))

    if books := get_deals_found_at(config.run_time):
        print_books(books)


if __name__ == '__main__':
    main()
