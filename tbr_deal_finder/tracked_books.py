import asyncio
import csv

from tqdm.asyncio import tqdm_asyncio

from tbr_deal_finder.book import Book, BookFormat, get_title_id
from tbr_deal_finder.retailer import Chirp, RETAILER_MAP
from tbr_deal_finder.config import Config
from tbr_deal_finder.library_exports import (
    get_book_authors,
    get_book_title,
    is_tbr_book,
    requires_audiobook_list_price_default
)
from tbr_deal_finder.retailer.models import Retailer
from tbr_deal_finder.utils import currency_to_float


def _library_export_tbr_books(config: Config, tbr_book_map: dict[str: Book]):
    """Adds tbr books in the library export to the provided tbr_book_map

    :param config:
    :param tbr_book_map:
    :return:
    """
    for library_export_path in config.library_export_paths:

        with open(library_export_path, 'r', newline='', encoding='utf-8') as file:
            # Use csv.DictReader to get dictionaries with column headers
            for book_dict in csv.DictReader(file):
                if not is_tbr_book(book_dict):
                    continue

                title = get_book_title(book_dict)
                authors = get_book_authors(book_dict)

                key = get_title_id(title, authors, BookFormat.NA)
                if key in tbr_book_map and tbr_book_map[key].audiobook_isbn:
                    continue

                tbr_book_map[key] = Book(
                    retailer="N/A",
                    title=title,
                    authors=authors,
                    list_price=0,
                    current_price=0,
                    timepoint=config.run_time,
                    format=BookFormat.NA,
                    audiobook_isbn=book_dict.get("audiobook_isbn"),
                    audiobook_list_price=currency_to_float(book_dict.get("audiobook_list_price") or 0),
                )


async def _apply_dynamic_audiobook_list_price(config: Config, tbr_book_map: dict[str: Book]):
    target_books = [
        book
        for book in tbr_book_map.values()
        if book.format == BookFormat.AUDIOBOOK
    ]
    if not target_books:
        return

    chirp = Chirp()
    semaphore = asyncio.Semaphore(5)
    books_with_pricing: list[Book] = await tqdm_asyncio.gather(
        *[
            chirp.get_book(book, config.run_time, semaphore)
            for book in target_books
        ],
        desc=f"Getting list prices for Libro.FM wishlist"
    )
    for book in books_with_pricing:
        tbr_book_map[book.title_id].audiobook_list_price = book.list_price


async def _retailer_wishlist(config: Config, tbr_book_map: dict[str: Book]):
    """Adds wishlist books in the library export to the provided tbr_book_map
    Books added here has the format the retailer sells (e.g. Audiobook)
    so deals are only checked for retailers with that type.

    For example,
    I as a user have Dune on my audible wishlist.
    I want to see deals for it on Libro because it's an audiobook.
    I don't want to see Kindle deals.

    :param config:
    :param tbr_book_map:
    :return:
    """
    for retailer_str in config.tracked_retailers:
        retailer: Retailer = RETAILER_MAP[retailer_str]()
        await retailer.set_auth()

        for book in (await retailer.get_wishlist(config)):
            na_key = get_title_id(book.title, book.authors, BookFormat.NA)
            if na_key in tbr_book_map:
                continue

            key = book.title_id
            if key in tbr_book_map and tbr_book_map[key].audiobook_isbn:
                continue

            tbr_book_map[key] = book

    if requires_audiobook_list_price_default(config):
        await _apply_dynamic_audiobook_list_price(config, tbr_book_map)


async def get_tbr_books(config: Config) -> list[Book]:
    tbr_book_map: dict[str: Book] = {}

    # Get TBRs specified in the user library (StoryGraph/GoodReads) export
    _library_export_tbr_books(config, tbr_book_map)

    # Pull wishlist from tracked retailers
    await _retailer_wishlist(config, tbr_book_map)

    return list(tbr_book_map.values())


