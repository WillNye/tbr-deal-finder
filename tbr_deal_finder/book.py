import dataclasses
import re
from datetime import datetime
from enum import Enum
from typing import Optional, Union

import click
from Levenshtein import ratio
from unidecode import unidecode

from tbr_deal_finder.config import Config
from tbr_deal_finder.utils import get_duckdb_conn, execute_query, get_query_by_name

_AUTHOR_RE = re.compile(r'[^a-zA-Z0-9]')

class BookFormat(Enum):
    AUDIOBOOK = "Audiobook"
    NA = "N/A"  # When format does not matter


@dataclasses.dataclass
class Book:    
    retailer: str
    title: str
    authors: str
    list_price: float
    current_price: float
    timepoint: datetime
    format: Union[BookFormat, str]

    # Metadata really only used for tracked books.
    # See get_tbr_books for more context
    audiobook_isbn: str = None
    audiobook_list_price: float = 0

    deleted: bool = False

    deal_id: Optional[str] = None
    exists: bool = True
    normalized_authors: list[str] = None

    def __post_init__(self):
        self.current_price = round(self.current_price, 2)
        self.list_price = round(self.list_price, 2)
        self.normalized_authors = get_normalized_authors(self.authors)

        # Strip the title down to its most basic repr
        # Improves hit rate on retailers
        self.title = self.title.split(":")[0].split("(")[0].strip()

        if not self.deal_id:
            self.deal_id = f"{self.title}__{self.normalized_authors}__{self.format}__{self.retailer}"

        if isinstance(self.format, str):
            self.format = BookFormat(self.format)

    def discount(self) -> int:
        return int((self.list_price/self.current_price - 1) * 100)

    @staticmethod
    def price_to_string(price: float) -> str:
        return f"{Config.currency_symbol()}{price:.2f}"

    @property
    def title_id(self) -> str:
        return f"{self.title}__{self.normalized_authors}__{self.format}"

    @property
    def full_title_str(self) -> str:
        return f"{self.title}__{self.normalized_authors}"

    def list_price_string(self):
        return self.price_to_string(self.list_price)

    def current_price_string(self):
        return self.price_to_string(self.current_price)

    def __str__(self) -> str:
        price = self.current_price_string()
        book_format = self.format.value
        title = self.title
        if len(self.title) > 75:
            title = f"{title[:75]}..."
        return f"{title} by {self.authors} - {price} - {self.discount()}% Off at {self.retailer} - {book_format}"

    def dict(self):
        response = dataclasses.asdict(self)
        response["format"] = self.format.value
        del response["audiobook_isbn"]
        del response["audiobook_list_price"]
        del response["exists"]
        del response["normalized_authors"]

        return response


def get_deals_found_at(timepoint: datetime) -> list[Book]:
    db_conn = get_duckdb_conn()
    query_response = execute_query(
        db_conn,
        get_query_by_name("get_deals_found_at.sql"),
        {"timepoint": timepoint}
    )
    return [Book(**book) for book in query_response]


def get_active_deals() -> list[Book]:
    db_conn = get_duckdb_conn()
    query_response = execute_query(
        db_conn,
        get_query_by_name("get_active_deals.sql")
    )
    return [Book(**book) for book in query_response]


def print_books(books: list[Book]):
    prior_title_id = books[0].title_id
    for book in books:
        if prior_title_id != book.title_id:
            prior_title_id = book.title_id
            click.echo()

        click.echo(str(book))


def get_full_title_str(title: str, authors: Union[list, str]) -> str:
    return f"{title}__{get_normalized_authors(authors)}"


def get_title_id(title: str, authors: Union[list, str], book_format: BookFormat) -> str:
    return f"{title}__{get_normalized_authors(authors)}__{book_format.value}"


def get_normalized_authors(authors: Union[str, list[str]]) -> list[str]:
    if isinstance(authors, str):
        authors = [i for i in authors.split(",")]

    return sorted([_AUTHOR_RE.sub('', unidecode(author)).lower() for author in authors])


def is_matching_authors(a1: list[str], a2: list[str]) -> bool:
    """Checks if two normalized authors are matching.
    Matching here means that they are at least 80% similar using levenshtein distance.

    Score is calculated as follows:
        1 - (distance / (len1 + len2))

    :param a1:
    :param a2:
    :return:
    """
    return any(
        any(ratio(author1, author2, score_cutoff=.8) for author2 in a2)
        for author1 in a1
    )
