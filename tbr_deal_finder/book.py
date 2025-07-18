import dataclasses
from datetime import datetime
from enum import Enum
from typing import Optional, Union

from tbr_deal_finder.utils import get_duckdb_conn, execute_query, get_query_by_name

class BookFormat(Enum):
    AUDIOBOOK = "Audiobook"


@dataclasses.dataclass
class Book:
    seller: str
    title: str
    authors: str
    list_price: float
    current_price: float
    timepoint: datetime
    format: Union[BookFormat, str]

    deleted: bool = False

    deal_id: Optional[str] = None
    exists: bool = True

    def __post_init__(self):
        if not self.deal_id:
            self.deal_id = f"{self.title}__{self.authors}__{self.seller}__{self.format}"

        if isinstance(self.format, str):
            self.format = BookFormat(self.format)

        self.current_price = round(self.current_price, 2)
        self.list_price = round(self.list_price, 2)

    def discount(self) -> int:
        return int((self.list_price/self.current_price - 1) * 100)

    @staticmethod
    def price_to_string(price: float) -> str:
        return f"${price:.2f}"

    @property
    def title_id(self) -> str:
        return f"{self.title}__{self.authors}__{self.format}"

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
        return f"{title} {book_format} by {self.authors} - {price} - {self.discount()}% Off at {self.seller}"

    def dict(self):
        response = dataclasses.asdict(self)
        response["format"] = self.format.value
        del response["exists"]

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
            print()

        print(str(book))
