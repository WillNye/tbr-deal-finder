import asyncio
import math
import os.path
from datetime import datetime
from textwrap import dedent
import readline  # type: ignore


import audible
import click
from audible.login import build_init_cookies

from tbr_deal_finder import TBR_DEALS_PATH
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import Retailer
from tbr_deal_finder.book import Book, BookFormat

_AUTH_PATH = TBR_DEALS_PATH.joinpath("audible.json")


def login_url_callback(url: str) -> str:
    """Helper function for login with external browsers."""

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        pass
    else:
        with sync_playwright() as p:
            iphone = p.devices["iPhone 12 Pro"]
            browser = p.webkit.launch(headless=False)
            context = browser.new_context(
                **iphone
            )
            cookies = []
            for name, value in build_init_cookies().items():
                cookies.append(
                    {
                        "name": name,
                        "value": value,
                        "url": url
                    }
                )
            context.add_cookies(cookies)
            page = browser.new_page()
            page.goto(url)

            while True:
                page.wait_for_timeout(600)
                if "/ap/maplanding" in page.url:
                    response_url = page.url
                    break

            browser.close()
        return response_url

    message = f"""\
        Please copy the following url and insert it into a web browser of your choice to log into Amazon.
        Note: your browser will show you an error page (Page not found). This is expected.
        
        {url}

        Once you have logged in, please insert the copied url.
    """
    click.echo(dedent(message))
    return input()


class Audible(Retailer):
    _auth: audible.Authenticator = None
    _client: audible.AsyncClient = None

    @property
    def name(self) -> str:
        return "Audible"

    @property
    def format(self) -> BookFormat:
        return BookFormat.AUDIOBOOK

    async def set_auth(self):
        if not os.path.exists(_AUTH_PATH):
            auth = audible.Authenticator.from_login_external(
                locale=Config.locale,
                login_url_callback=login_url_callback
            )

            # Save credentials to file
            auth.to_file(_AUTH_PATH)

        self._auth = audible.Authenticator.from_file(_AUTH_PATH)
        self._client = audible.AsyncClient(auth=self._auth)

    async def get_book(
        self,
        target: Book,
        runtime: datetime,
        semaphore: asyncio.Semaphore
    ) -> Book:
        title = target.title
        authors = target.authors

        async with semaphore:
            match = await self._client.get(
                "1.0/catalog/products",
                num_results=50,
                author=authors,
                title=title,
                response_groups=[
                    "contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans"
                ]
            )

            for product in match.get("products", []):
                if product["title"] != title:
                    continue

                return Book(
                    retailer=self.name,
                    title=title,
                    authors=authors,
                    list_price=product["price"]["list_price"]["base"],
                    current_price=product["price"]["lowest_price"]["base"],
                    timepoint=runtime,
                    format=BookFormat.AUDIOBOOK
                )

            return Book(
                retailer=self.name,
                title=title,
                authors=authors,
                list_price=0,
                current_price=0,
                timepoint=runtime,
                format=BookFormat.AUDIOBOOK,
                exists=False,
            )

    async def get_wishlist(self, config: Config) -> list[Book]:
        wishlist_books = []

        page = 0
        total_pages = 1
        page_size = 50
        while page < total_pages:
            response = await self._client.get(
                "1.0/wishlist",
                num_results=page_size,
                page=page,
                response_groups=[
                    "contributors, product_attrs, product_desc, product_extended_attrs"
                ]
            )

            for audiobook in response.get("products", []):
                authors = [author["name"] for author in audiobook["authors"]]
                wishlist_books.append(
                    Book(
                        retailer=self.name,
                        title=audiobook["title"],
                        authors=", ".join(authors),
                        list_price=1,
                        current_price=1,
                        timepoint=config.run_time,
                        format=self.format,
                        audiobook_isbn=audiobook["isbn"],
                    )
                )

            page += 1
            total_pages = math.ceil(int(response.get("total_results", 1))/page_size)

        return wishlist_books

    async def get_library(self, config: Config) -> list[Book]:
        library_books = []

        page = 1
        total_pages = 1
        page_size = 1000
        while page <= total_pages:
            response = await self._client.get(
                "1.0/library",
                num_results=page_size,
                page=page,
                response_groups=[
                    "contributors, product_attrs, product_desc, product_extended_attrs"
                ]
            )

            for audiobook in response.get("items", []):
                authors = [author["name"] for author in audiobook["authors"]]
                library_books.append(
                    Book(
                        retailer=self.name,
                        title=audiobook["title"],
                        authors=", ".join(authors),
                        list_price=1,
                        current_price=1,
                        timepoint=config.run_time,
                        format=self.format,
                        audiobook_isbn=audiobook["isbn"],
                    )
                )

            page += 1
            total_pages = math.ceil(int(response.get("total_results", 1))/page_size)

        return library_books
