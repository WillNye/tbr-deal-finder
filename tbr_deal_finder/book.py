import dataclasses
import re
from datetime import datetime
from enum import Enum
from typing import Optional, Union

import click
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
    audiobook_isbn: str = None

    deleted: bool = False

    deal_id: Optional[str] = None
    exists: bool = True
    normalized_authors: list[str] = None

    def __post_init__(self):
        if not self.deal_id:
            self.deal_id = f"{self.title}__{self.normalized_authors}__{self.retailer}__{self.format}"

        if isinstance(self.format, str):
            self.format = BookFormat(self.format)

        self.current_price = round(self.current_price, 2)
        self.list_price = round(self.list_price, 2)
        self.normalized_authors = get_normalized_authors(self.authors)

    def discount(self) -> int:
        return int((self.list_price/self.current_price - 1) * 100)

    @staticmethod
    def price_to_string(price: float) -> str:
        return f"{Config.currency_symbol()}{price:.2f}"

    @property
    def title_id(self) -> str:
        return f"{self.title}__{self.normalized_authors}__{self.format}"

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


def get_normalized_authors(authors: Union[str, list[str]]) -> list[str]:
    if isinstance(authors, str):
        authors = [i for i in authors.split(",")]

    return sorted([_AUTHOR_RE.sub('', unidecode(author)).lower() for author in authors])
