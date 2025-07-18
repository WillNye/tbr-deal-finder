import csv

from tqdm import tqdm

from tbr_deal_finder.config import Config


def set_book_audio_isbn(book: dict) -> dict:
    """Get ISBN13 info for book
    Required for Libro.fm
    """
    title = book["Title"]
    authors = book["Authors"]

    # TODO: Function to get books with their ISBN13

    books = []
    if not books:
        return book

    for b in books:
        isbn = ""  # TODO: Extract ISBN from `b`
        if b["title"] and b["title"] in title and b["author"] in authors:
            book["audio_isbn"] = isbn
            return book

    book["audio_isbn"] = ""
    return book


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
