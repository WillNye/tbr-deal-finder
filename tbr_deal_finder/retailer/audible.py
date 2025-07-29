import asyncio
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
        use_playwright = True
    except ImportError:
        use_playwright = False

    if use_playwright:
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

            if not match["products"]:
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

            for product in match["products"]:
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
