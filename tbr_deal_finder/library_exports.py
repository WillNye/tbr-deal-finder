import asyncio
import csv
import shutil
import tempfile

from tqdm.asyncio import tqdm_asyncio

from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.librofm import LibroFM


def _get_book_authors(book: dict) -> str:
    if authors := book.get('Authors'):
        return authors

    authors = book['Author']
    if additional_authors := book.get("Additional Authors"):
        authors = f"{authors}, {additional_authors}"

    return authors


def _get_book_title(book: dict) -> str:
    title = book['Title']
    return title.split("(")[0].strip()


def _is_tbr_book(book: dict) -> bool:
    if "Read Status" in book:
        return book["Read Status"] == "to-read"
    elif "Bookshelves" in book:
        return "to-read" in book["Bookshelves"]
    else:
        return True


def get_tbr_books(config: Config) -> list[Book]:
    tbr_book_map: dict[str: Book] = {}
    for library_export_path in config.library_export_paths:

        with open(library_export_path, 'r', newline='', encoding='utf-8') as file:
            # Use csv.DictReader to get dictionaries with column headers
            for book_dict in csv.DictReader(file):
                if not _is_tbr_book(book_dict):
                    continue

                title = _get_book_title(book_dict)
                authors = _get_book_authors(book_dict)
                key = f'{title}__{authors}'

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
                    audiobook_isbn=book_dict["audiobook_isbn"],
                )
    return list(tbr_book_map.values())


async def maybe_set_library_export_audiobook_isbn(config: Config):
    """To get the price from Libro.fm for a book you need its ISBN

    As opposed to trying to get that every time latest-deals is run
        we're just updating the export csv once to include the ISBN.
    """

    if "Libro.FM" not in config.tracked_retailers:
        return

    books_requiring_check_map = dict()
    book_to_isbn_map = dict()


    for library_export_path in config.library_export_paths:
        with open(library_export_path, 'r', newline='', encoding='utf-8') as file:
            # Use csv.DictReader to get dictionaries with column headers
            for book_dict in csv.DictReader(file):
                if not _is_tbr_book(book_dict):
                    continue

                title = _get_book_title(book_dict)
                authors = _get_book_authors(book_dict)
                key = f'{title}__{authors}'

                if "audiobook_isbn" in book_dict:
                    book_to_isbn_map[key] = book_dict["audiobook_isbn"]
                    books_requiring_check_map.pop(key, None)
                elif key not in book_to_isbn_map:
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
        return

    libro_fm = LibroFM()
    # Setting it lower to be a good user of libro on their more expensive search call
    semaphore = asyncio.Semaphore(3)

    # Set the audiobook isbn for Book instances in books_requiring_check_map
    await tqdm_asyncio.gather(
        *[
            libro_fm.get_book_isbn(book, semaphore) for book in books_requiring_check_map.values()
        ],
        desc="Getting required audiobook ISBN info"
    )

    # Go back and now add the audiobook_isbn
    for library_export_path in config.library_export_paths:
        with open(library_export_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            field_names = list(reader.fieldnames) + ["audiobook_isbn"]
            file_content = [book_dict for book_dict in reader]
            if not file_content or "audiobook_isbn" in file_content[0]:
                continue

            with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='') as temp_file:
                temp_filename = temp_file.name
                writer = csv.DictWriter(temp_file, fieldnames=field_names)
                writer.writeheader()

                for book_dict in file_content:
                    if _is_tbr_book(book_dict):
                        title = _get_book_title(book_dict)
                        authors = _get_book_authors(book_dict)
                        key = f'{title}__{authors}'

                        if key in book_to_isbn_map:
                            audiobook_isbn = book_to_isbn_map[key]
                        else:
                            book = books_requiring_check_map[key]
                            audiobook_isbn = book.audiobook_isbn

                        book_dict["audiobook_isbn"] = audiobook_isbn
                    else:
                        book_dict["audiobook_isbn"] = ""

                    writer.writerow(book_dict)

        shutil.move(temp_filename, library_export_path)

