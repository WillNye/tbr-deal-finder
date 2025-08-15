import asyncio
import json
import os
import urllib.parse
from datetime import datetime, timedelta

import click

from tbr_deal_finder import TBR_DEALS_PATH
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import AioHttpSession, Retailer
from tbr_deal_finder.book import Book, BookFormat, get_normalized_authors, is_matching_authors, get_normalized_title
from tbr_deal_finder.utils import currency_to_float


class LibroFM(AioHttpSession, Retailer):
    BASE_URL = "https://libro.fm"
    USER_AGENT = "okhttp/3.14.9"
    USER_AGENT_DOWNLOAD = (
        "AndroidDownloadManager/11 (Linux; U; Android 11; "
        "Android SDK built for x86_64 Build/RSR1.210722.013.A2)"
    )
    CLIENT_VERSION = (
        "Android: Libro.fm 7.6.1 Build: 194 Device: Android SDK built for x86_64 "
        "(unknown sdk_phone_x86_64) AndroidOS: 11 SDK: 30"
    )

    def __init__(self):
        super().__init__()

        self.auth_token = None

    @property
    def name(self) -> str:
        return "Libro.FM"

    @property
    def format(self) -> BookFormat:
        return BookFormat.AUDIOBOOK

    async def make_request(self, url_path: str, request_type: str, **kwargs) -> dict:
        url = urllib.parse.urljoin(self.BASE_URL, url_path)
        headers = kwargs.pop("headers", {})
        headers["User-Agent"] = self.USER_AGENT
        if self.auth_token:
            headers["authorization"] = f"Bearer {self.auth_token}"

        session = await self._get_session()
        response = await session.request(
            request_type.upper(),
            url,
            headers=headers,
            **kwargs
        )
        if response.ok:
            return await response.json()
        else:
            return {}

    async def set_auth(self):
        auth_path = TBR_DEALS_PATH.joinpath("libro_fm.json")
        if os.path.exists(auth_path):
            with open(auth_path, "r") as f:
                auth_info = json.load(f)
                token_created_at = datetime.fromtimestamp(auth_info["created_at"])
                max_token_age = datetime.now() - timedelta(days=5)
                if token_created_at > max_token_age:
                    self.auth_token = auth_info["access_token"]
                    return

        response = await self.make_request(
            "/oauth/token",
            "POST",
            json={
                "grant_type": "password",
                "username": click.prompt("Libro FM Username"),
                "password": click.prompt("Libro FM Password", hide_input=True),
            }
        )
        self.auth_token = response["access_token"]
        with open(auth_path, "w") as f:
            json.dump(response, f)

    async def get_book_isbn(self, book: Book, semaphore: asyncio.Semaphore) -> Book:
        # runtime isn't used but get_book_isbn must follow the get_book method signature.

        title = book.title

        async with semaphore:
            response = await self.make_request(
                f"api/v10/explore/search",
                "GET",
                params={
                    "q": title,
                    "searchby": "titles",
                    "sortby": "relevance#results",
                },
            )

        for b in response["audiobook_collection"]["audiobooks"]:
            normalized_authors = get_normalized_authors(b["authors"])

            if (
                title == get_normalized_title(b["title"])
                and is_matching_authors(book.normalized_authors, normalized_authors)
            ):
                book.audiobook_isbn = b["isbn"]
                break

        return book

    async def get_book(
        self, target: Book, semaphore: asyncio.Semaphore
    ) -> Book:
        if not target.audiobook_isbn:
            target.exists = False
            return target

        async with semaphore:
            response = await self.make_request(
                f"api/v10/explore/audiobook_details/{target.audiobook_isbn}",
                "GET"
            )

        if response:
            target.list_price = target.audiobook_list_price
            target.current_price = currency_to_float(response["data"]["purchase_info"]["price"])
            return target

        target.exists = False
        return target

    async def get_wishlist(self, config: Config) -> list[Book]:
        wishlist_books = []

        page = 1
        total_pages = 1
        while page <= total_pages:
            response = await self.make_request(
                f"api/v10/explore/wishlist",
                "GET",
                params=dict(page=page)
            )
            wishlist = response.get("data", {}).get("wishlist", {})
            if not wishlist:
                return []

            for book in wishlist.get("audiobooks", []):
                wishlist_books.append(
                    Book(
                        retailer=self.name,
                        title=book["title"],
                        authors=", ".join(book["authors"]),
                        list_price=1,
                        current_price=1,
                        timepoint=config.run_time,
                        format=self.format,
                        audiobook_isbn=book["isbn"],
                    )
                )

            page += 1
            total_pages = wishlist["total_pages"]

        return wishlist_books

    async def get_library(self, config: Config) -> list[Book]:
        library_books = []

        page = 1
        total_pages = 1
        while page <= total_pages:
            response = await self.make_request(
                f"api/v10/library",
                "GET",
                params=dict(page=page)
            )

            for book in response.get("audiobooks", []):
                library_books.append(
                    Book(
                        retailer=self.name,
                        title=book["title"],
                        authors=", ".join(book["authors"]),
                        list_price=1,
                        current_price=1,
                        timepoint=config.run_time,
                        format=self.format,
                        audiobook_isbn=book["isbn"],
                    )
                )

            page += 1
            total_pages = response["total_pages"]

        return library_books
