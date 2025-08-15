import asyncio
import copy
import csv
from collections import defaultdict
from typing import Callable, Awaitable, Optional

import pandas as pd
from tqdm.asyncio import tqdm_asyncio

from tbr_deal_finder.book import Book, BookFormat, get_title_id
from tbr_deal_finder.owned_books import get_owned_books
from tbr_deal_finder.retailer import Chirp, RETAILER_MAP, LibroFM, Kindle
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import Retailer
from tbr_deal_finder.utils import execute_query, get_duckdb_conn


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
                if key in tbr_book_map:
                    continue

                tbr_book_map[key] = Book(
                    retailer="N/A",
                    title=title,
                    authors=authors,
                    list_price=0,
                    current_price=0,
                    timepoint=config.run_time,
                    format=BookFormat.NA,
                )


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


async def _get_raw_tbr_books(config: Config) -> list[Book]:
    """Gets books in any library export or tracked retailer wishlist

    Excludes books in the format they are owned.
    Example: User owns Dungeon Crawler Carl Audiobook but it's on the user TBR.
        Result - Deals will be tracked for the Dungeon Crawler Carl EBook (if tracking kindle deals)

    :param config:
    :return:
    """

    owned_books = await get_owned_books(config)
    tracking_audiobooks = config.is_tracking_format(book_format=BookFormat.AUDIOBOOK)
    tracking_ebooks = config.is_tracking_format(book_format=BookFormat.EBOOK)

    tbr_book_map: dict[str: Book] = {}
    # Get TBRs specified in the user library (StoryGraph/GoodReads) export
    _library_export_tbr_books(config, tbr_book_map)
    # Pull wishlist from tracked retailers
    await _retailer_wishlist(config, tbr_book_map)
    raw_tbr_books = list(tbr_book_map.values())

    response: list[Book] = []

    owned_book_title_map: dict[str, set] = defaultdict(set)
    for book in owned_books:
        owned_book_title_map[book.full_title_str].add(book.format)

    for book in raw_tbr_books:
        owned_formats = owned_book_title_map.get(book.full_title_str)
        if not owned_formats:
            response.append(book)
        elif BookFormat.NA in owned_formats:
            continue
        elif tracking_audiobooks and BookFormat.AUDIOBOOK not in owned_formats:
            book.format = BookFormat.AUDIOBOOK
            response.append(book)
        elif tracking_ebooks and BookFormat.EBOOK not in owned_formats:
            book.format = BookFormat.EBOOK
            response.append(book)

    return response


async def _set_tbr_book_attr(
    tbr_books: list[Book],
    target_attr: str,
    get_book_callable: Callable[[Book, asyncio.Semaphore], Awaitable[Book]],
    tbr_book_attr: Optional[str] = None
):
    if not tbr_books:
        return

    if not tbr_book_attr:
        tbr_book_attr = target_attr

    tbr_books_map = {b.full_title_str: b for b in tbr_books}
    tbr_books_copy = copy.deepcopy(tbr_books)
    semaphore = asyncio.Semaphore(5)
    human_readable_name = target_attr.replace("_", " ").title()

    # Get books with the appropriate transform applied
    # Responsibility is on the callable here
    enriched_books = await tqdm_asyncio.gather(
        *[
            get_book_callable(book, semaphore) for book in tbr_books_copy
        ],
        desc=f"Getting required {human_readable_name} info"
    )
    for enriched_book in enriched_books:
        book = tbr_books_map[enriched_book.full_title_str]
        setattr(
            book,
            tbr_book_attr,
            getattr(enriched_book, target_attr)
        )


def _requires_audiobook_list_price(config: Config):
    return bool(
        "Libro.FM" in config.tracked_retailers
        and "Audible" not in config.tracked_retailers
        and "Chirp" not in config.tracked_retailers
    )


async def _maybe_set_audiobook_list_price(config: Config, new_tbr_books: list[Book]):
    """Set a default list price for audiobooks

    Only set if not currently set and the only audiobook retailer is Libro.FM
    Libro.FM doesn't include the actual default price in its response, so this grabs the price reported by Chirp.
    Chirp doesn't require a login to get this price info making it ideal in this instance.

    :param config:
    :return:
    """
    if not _requires_audiobook_list_price(config):
        return

    chirp = Chirp()
    relevant_tbr_books = [
        book
        for book in new_tbr_books
        if book.format in [BookFormat.AUDIOBOOK, BookFormat.NA]
    ]

    await _set_tbr_book_attr(
        relevant_tbr_books,
        "list_price",
        chirp.get_book,
        "audiobook_list_price"
    )


async def _maybe_set_audiobook_isbn(config: Config, new_tbr_books: list[Book]):
    """To get the price from Libro.fm for a book, you need its ISBN
    """
    if "Libro.FM" not in config.tracked_retailers:
        return

    libro_fm = LibroFM()
    await libro_fm.set_auth()

    relevant_tbr_books = [
        book
        for book in new_tbr_books
        if book.format in [BookFormat.AUDIOBOOK, BookFormat.NA]
    ]

    await _set_tbr_book_attr(
        relevant_tbr_books,
        "audiobook_isbn",
        libro_fm.get_book_isbn,
    )


async def _maybe_set_ebook_asin(config: Config, new_tbr_books: list[Book]):
    """To get the price from kindle for a book, you need its asin
    """
    if "Kindle" not in config.tracked_retailers:
        return

    kindle = Kindle()
    await kindle.set_auth()

    relevant_tbr_books = [
        book
        for book in new_tbr_books
        if book.format in [BookFormat.EBOOK, BookFormat.NA]
    ]

    await _set_tbr_book_attr(
        relevant_tbr_books,
        "ebook_asin",
        kindle.get_book_asin,
    )


def get_book_authors(book: dict) -> str:
    if authors := book.get('Authors'):
        return authors

    authors = book['Author']
    if additional_authors := book.get("Additional Authors"):
        authors = f"{authors}, {additional_authors}"

    return authors


def get_book_title(book: dict) -> str:
    title = book['Title']
    return title.split("(")[0].strip()


def is_tbr_book(book: dict) -> bool:
    if "Read Status" in book:
        return book["Read Status"] == "to-read"
    elif "Bookshelves" in book:
        return "to-read" in book["Bookshelves"]
    else:
        return True


def reprocess_incomplete_tbr_books(config: Config):
    db_conn = get_duckdb_conn()

    if config.is_tracking_format(BookFormat.EBOOK):
        # Replace any tbr_books missing required attr
        db_conn.execute(
            "DELETE FROM tbr_book WHERE ebook_asin IS NULL AND format != $book_format",
            parameters=dict(book_format=BookFormat.AUDIOBOOK.value)
        )

    if LibroFM().name in config.tracked_retailers:
        # Replace any tbr_books missing required attr
        db_conn.execute(
            "DELETE FROM tbr_book WHERE audiobook_isbn IS NULL AND format != $book_format",
            parameters=dict(book_format=BookFormat.EBOOK.value)
        )

    if _requires_audiobook_list_price(config):
        # Replace any tbr_books missing required attr
        db_conn.execute(
            "DELETE FROM tbr_book WHERE audiobook_list_price IS NULL AND format != $book_format",
            parameters=dict(book_format=BookFormat.EBOOK.value)
        )


async def sync_tbr_books(config: Config):
    raw_tbr_books = await _get_raw_tbr_books(config)
    db_conn = get_duckdb_conn()

    if not raw_tbr_books:
        return

    df = pd.DataFrame([book.tbr_dict() for book in raw_tbr_books])
    db_conn.register("_df", df)
    db_conn.execute("CREATE OR REPLACE TABLE _latest_tbr_book AS SELECT * FROM _df;")
    db_conn.unregister("_df")

    # Remove books no longer on user tbr
    db_conn.execute(
        "DELETE FROM tbr_book WHERE book_id NOT IN (SELECT book_id FROM _latest_tbr_book)"
    )

    # Remove books from _latest_tbr_book for further processing for books already in tbr_book
    db_conn.execute(
        "DELETE FROM _latest_tbr_book WHERE book_id IN (SELECT book_id FROM tbr_book)"
    )

    new_tbr_book_data = execute_query(
        db_conn,
        "SELECT * EXCLUDE(book_id) FROM _latest_tbr_book"
    )

    new_tbr_books = [Book(retailer="N/A", timepoint=config.run_time, **b) for b in new_tbr_book_data]
    if not new_tbr_books:
        return

    await _maybe_set_audiobook_list_price(config, new_tbr_books)
    await _maybe_set_audiobook_isbn(config, new_tbr_books)
    await _maybe_set_ebook_asin(config, new_tbr_books)

    df = pd.DataFrame([book.tbr_dict() for book in new_tbr_books])
    db_conn.register("_df", df)
    db_conn.execute("INSERT INTO tbr_book SELECT * FROM _df;")
    db_conn.unregister("_df")


async def get_tbr_books(config: Config) -> list[Book]:
    await sync_tbr_books(config)

    db_conn = get_duckdb_conn()
    tbr_book_data = execute_query(
        db_conn,
        "SELECT * EXCLUDE(book_id) FROM tbr_book"
    )

    return [Book(retailer="N/A", timepoint=config.run_time, **b) for b in tbr_book_data]
