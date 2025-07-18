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

