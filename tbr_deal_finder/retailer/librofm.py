import asyncio
import json
import os
import urllib.parse
from datetime import datetime, timedelta

import aiohttp
import click

from tbr_deal_finder import TBR_DEALS_PATH
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import Retailer
from tbr_deal_finder.book import Book, BookFormat, get_normalized_authors
from tbr_deal_finder.utils import currency_to_float


class LibroFM(Retailer):
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

        async with aiohttp.ClientSession() as http_client:
            response = await http_client.request(
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
        self.auth_token = response
        with open(auth_path, "w") as f:
            json.dump(response, f)

    async def get_book_isbn(self, book: Book, runtime: datetime, semaphore: asyncio.Semaphore) -> Book:
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
                title == b["title"]
                and any(author in normalized_authors for author in book.normalized_authors)
            ):
                book.audiobook_isbn = b["isbn"]
                break

        return book

    async def get_book(
        self, target: Book, runtime: datetime, semaphore: asyncio.Semaphore
    ) -> Book:
        if target.format == BookFormat.AUDIOBOOK and not target.audiobook_isbn:
            # When "format" is AUDIOBOOK here that means the target was pulled from an audiobook retailer wishlist
            # In this flow, there is no attempt to resolve the isbn ahead of time, so it's done here instead.
            await self.get_book_isbn(target, runtime, semaphore)

        if not target.audiobook_isbn:
            return Book(
                retailer=self.name,
                title=target.title,
                authors=target.authors,
                list_price=0,
                current_price=0,
                timepoint=runtime,
                format=BookFormat.AUDIOBOOK,
                exists=False,
            )

        async with semaphore:
            response = await self.make_request(
                f"api/v10/explore/audiobook_details/{target.audiobook_isbn}",
                "GET"
            )

        if response:
            return Book(
                retailer=self.name,
                title=target.title,
                authors=target.authors,
                list_price=target.audiobook_list_price,
                current_price=currency_to_float(response["data"]["purchase_info"]["price"]),
                timepoint=runtime,
                format=BookFormat.AUDIOBOOK,
            )

        return Book(
            retailer=self.name,
            title=target.title,
            authors=target.authors,
            list_price=0,
            current_price=0,
            timepoint=runtime,
            format=BookFormat.AUDIOBOOK,
            exists=False,
        )

    async def get_wishlist(self, config: Config) -> list[Book]:
        wishlist_books = []

        page = 1
        total_pages = 1
        while page <= total_pages:
            response = await self.make_request(
                f"api/v10/explore/wishlist",
                "GET",
                params=dict(page=2)
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
