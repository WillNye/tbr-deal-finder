import asyncio
import os.path
from datetime import datetime
from textwrap import dedent
import readline  # type: ignore


import audible
from audible.login import playwright_external_login_url_callback

from tbr_deal_finder import TBR_DEALS_PATH
from tbr_deal_finder.seller.models import Seller
from tbr_deal_finder.book import Book, BookFormat

_AUTH_PATH = TBR_DEALS_PATH.joinpath("audible.json")


def login_url_callback(url: str) -> str:
    """Helper function for login with external browsers."""
    try:
        return playwright_external_login_url_callback(url)
    except ImportError:
        pass

    message = f"""\
        Please copy the following url and insert it into a web browser of your choice to log into Amazon.
        Note: your browser will show you an error page (Page not found). This is expected.
        
        {url}

        Once you have logged in, please insert the copied url.
    """
    print(dedent(message))
    return input()


class Audible(Seller):
    _auth: audible.Authenticator = None
    _client: audible.AsyncClient = None

    @property
    def name(self) -> str:
        return "Audible"

    async def get_audio_book(
            self, title: str, authors: str, runtime: datetime, semaphore: asyncio.Semaphore
    ) -> Union[Book, None]:
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
                print(f"{title} - {authors} - Not Found")
                return None

            for product in match["products"]:
                if product["title"] != title:
                    continue

                return Book(
                    seller=self.name,
                    title=title,
                    authors=authors,
                    list_price=product["price"]["list_price"]["base"],
                    current_price=product["price"]["lowest_price"]["base"],
                    timepoint=runtime,
                    format=BookFormat.AUDIOBOOK
                )

            default_product = match["products"][0]
            if title.strip().lower() not in default_product["title"].strip().lower():
                print(f"{title} - {authors} - Not Found")
                return None

            # return Book(
            #     seller=self.name,
            #     title=title,
            #     authors=authors,
            #     list_price=default_product["price"]["list_price"]["base"],
            #     current_price=default_product["price"]["lowest_price"]["base"],
            #     timepoint=runtime,
            #     format=BookFormat.AUDIOBOOK
            # )
            print(f"{title} - {authors} - Not Found")
            return None

    async def set_auth(self):
        if not os.path.exists(_AUTH_PATH):
            auth = audible.Authenticator.from_login_external(
                locale="us",
                login_url_callback=login_url_callback
            )

            # Save credentials to file
            auth.to_file(_AUTH_PATH)

        self._auth = audible.Authenticator.from_file(_AUTH_PATH)
        self._client = audible.AsyncClient(auth=self._auth)
