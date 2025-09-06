import asyncio
import json
import os
import urllib.parse
from datetime import datetime, timedelta
from typing import Union

import click

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import AioHttpSession, Retailer, GuiAuthContext
from tbr_deal_finder.book import Book, BookFormat, get_normalized_authors, is_matching_authors, get_normalized_title
from tbr_deal_finder.utils import currency_to_float, echo_err


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

    def user_is_authed(self) -> bool:
        if os.path.exists(self.auth_path):
            with open(self.auth_path, "r") as f:
                auth_info = json.load(f)
                token_created_at = datetime.fromtimestamp(auth_info["created_at"])
                max_token_age = datetime.now() - timedelta(days=7)
                if token_created_at > max_token_age:
                    self.auth_token = auth_info["access_token"]
                    return True

        return False

    async def set_auth(self):
        if self.user_is_authed():
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
        if "access_token" not in response:
            echo_err("Login failed. Try again.")
            await self.set_auth()

        self.auth_token = response["access_token"]
        with open(self.auth_path, "w") as f:
            json.dump(response, f)

    @property
    def gui_auth_context(self) -> GuiAuthContext:
        return GuiAuthContext(
            title="Login to Libro.FM",
            fields=[
                {"name": "username", "label": "Username", "type": "text"},
                {"name": "password", "label": "Password", "type": "password"}
            ]
        )

    async def gui_auth(self, form_data: dict) -> bool:
        response = await self.make_request(
            "/oauth/token",
            "POST",
            json={
                "grant_type": "password",
                "username": form_data["username"],
                "password": form_data["password"],
            }
        )
        if "access_token" not in response:
            return False

        self.auth_token = response["access_token"]
        with open(self.auth_path, "w") as f:
            json.dump(response, f)
        return True

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
    ) -> Union[Book, None]:
        if not target.audiobook_isbn:
            target.exists = False
            return target

        async with semaphore:
            for _ in range(10):
                response = await self.make_request(
                    f"api/v10/explore/audiobook_details/{target.audiobook_isbn}",
                    "GET"
                )

                if response:
                    target.list_price = target.audiobook_list_price
                    target.current_price = currency_to_float(response["data"]["purchase_info"]["price"])
                    return target

        return None

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
