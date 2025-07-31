import asyncio
import csv
import shutil
import tempfile
from datetime import datetime
from typing import Callable, Awaitable, Optional

from tqdm.asyncio import tqdm_asyncio

from tbr_deal_finder.book import Book, BookFormat, get_normalized_authors
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer import LibroFM, Chirp


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


def requires_audiobook_list_price_default(config: Config) -> bool:
    return bool(
        "Libro.FM" in config.tracked_retailers
        and "Audible" not in config.tracked_retailers
        and "Chirp" not in config.tracked_retailers
    )


async def _maybe_set_column_for_library_exports(
    config: Config,
    attr_name: str,
    get_book_callable: Callable[[Book, datetime, asyncio.Semaphore], Awaitable[Book]],
    column_name: Optional[str] = None,
):
    """Adds a new column to all library exports that are missing it.
    Uses get_book_callable to set the column value if a matching record couldn't be found
    on that column in any other library export file.

    :param config:
    :param attr_name:
    :param get_book_callable:
    :param column_name:
    :return:
    """
    if not column_name:
        column_name = attr_name

    books_requiring_check_map = dict()
    book_to_col_val_map = dict()

    # Iterate all library export paths
    for library_export_path in config.library_export_paths:
        with open(library_export_path, 'r', newline='', encoding='utf-8') as file:
            # Use csv.DictReader to get dictionaries with column headers
            for book_dict in csv.DictReader(file):
                if not is_tbr_book(book_dict):
                    continue

                title = get_book_title(book_dict)
                authors = get_book_authors(book_dict)
                key = f'{title}__{get_normalized_authors(authors)}'

                if column_name in book_dict:
                    # Keep state of value for this book/key
                    # in the event another export has the same book but the value is not set
                    book_to_col_val_map[key] = book_dict[column_name]
                    # Value has been found so a check no longer needs to be performed
                    books_requiring_check_map.pop(key, None)
                elif key not in book_to_col_val_map:
                    # Not found, add the book to those requiring the column val to be set
                    books_requiring_check_map[key] = Book(
                        retailer="N/A",
                        title=title,
                        authors=authors,
                        list_price=0,
                        current_price=0,
                        timepoint=config.run_time,
                        format=BookFormat.NA
                    )

    if not books_requiring_check_map:
        # Everything was resolved, nothing else to do
        return

    semaphore = asyncio.Semaphore(5)
    human_readable_name = attr_name.replace("_", " ").title()

    # Get books with the appropriate transform applied
    # Responsibility is on the callable here
    enriched_books = await tqdm_asyncio.gather(
        *[
            get_book_callable(book, config.run_time, semaphore) for book in books_requiring_check_map.values()
        ],
        desc=f"Getting required {human_readable_name} info"
    )
    updated_book_map = {
        b.full_title_str: b
        for b in enriched_books
    }


    # Go back and now add the new column where it hasn't been set
    for library_export_path in config.library_export_paths:
        with open(library_export_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            field_names = list(reader.fieldnames) + [column_name]
            file_content = [book_dict for book_dict in reader]
            if not file_content or column_name in file_content[0]:
                continue

            with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='') as temp_file:
                temp_filename = temp_file.name
                writer = csv.DictWriter(temp_file, fieldnames=field_names)
                writer.writeheader()

                for book_dict in file_content:
                    if is_tbr_book(book_dict):
                        title = get_book_title(book_dict)
                        authors = get_book_authors(book_dict)
                        key = f'{title}__{get_normalized_authors(authors)}'

                        if key in book_to_col_val_map:
                            col_val = book_to_col_val_map[key]
                        elif key in updated_book_map:
                            book = updated_book_map[key]
                            col_val = getattr(book, attr_name)
                        else:
                            col_val = ""

                        book_dict[column_name] = col_val
                    else:
                        book_dict[column_name] = ""

                    writer.writerow(book_dict)

        shutil.move(temp_filename, library_export_path)


async def _maybe_set_library_export_audiobook_isbn(config: Config):
    """To get the price from Libro.fm for a book, you need its ISBN

    As opposed to trying to get that every time latest-deals is run
        we're just updating the export csv once to include the ISBN.

    Unfortunately, we do have to get it at run time for wishlists.
    """
    if "Libro.FM" not in config.tracked_retailers:
        return

    libro_fm = LibroFM()
    await libro_fm.set_auth()

    await _maybe_set_column_for_library_exports(
        config,
        "audiobook_isbn",
        libro_fm.get_book_isbn,
    )


async def _maybe_set_library_export_audiobook_list_price(config: Config):
    """Set a default list price for audiobooks

    Only set if not currently set and the only audiobook retailer is Libro.FM
    Libro.FM doesn't include the actual default price in its response, so this grabs the price reported by Chirp.
    Chirp doesn't require a login to get this price info making it ideal in this instance.

    :param config:
    :return:
    """
    if not requires_audiobook_list_price_default(config):
        return

    chirp = Chirp()
    await chirp.set_auth()

    await _maybe_set_column_for_library_exports(
        config,
        "list_price",
        chirp.get_book,
        "audiobook_list_price"
    )


async def maybe_enrich_library_exports(config: Config):
    await _maybe_set_library_export_audiobook_isbn(config)
    await _maybe_set_library_export_audiobook_list_price(config)
