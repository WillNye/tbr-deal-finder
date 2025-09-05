import asyncio
import json
from typing import Union

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.amazon import Amazon, AUTH_PATH
from tbr_deal_finder.book import Book, BookFormat, get_normalized_title, get_normalized_authors, is_matching_authors


class Kindle(Amazon):

    def __init__(self):
        self._headers = {}

    @property
    def name(self) -> str:
        return "Kindle"

    @property
    def format(self) -> BookFormat:
        return BookFormat.EBOOK

    @property
    def max_concurrency(self) -> int:
        return 3

    def _get_base_url(self) -> str:
        return f"https://www.amazon.{self._auth.locale.domain}"

    def _get_read_base_url(self) -> str:
        return f"https://read.amazon.{self._auth.locale.domain}"

    async def set_auth(self):
        await super().set_auth()

        with open(AUTH_PATH, "r") as f:
            auth_info = json.load(f)

            cookies = auth_info["website_cookies"]
            cookies["x-access-token"] = auth_info["access_token"]

        self._headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Kindle) AppleWebKit/537.3",
            "Accept": "application/json, */*",
            "Cookie": "; ".join([f"{k}={v}" for k, v in cookies.items()])
        }


    async def get_book_asin(
        self,
        target: Book,
        semaphore: asyncio.Semaphore
    ) -> Book:
        title = target.title
        async with semaphore:
            match = await self._client.get(
                f"{self._get_base_url()}/kindle-dbs/kws?userCode=AndroidKin&deviceType=A3VNNDO1I14V03&node=2671536011&excludedNodes=&page=1&size=20&autoSpellCheck=1&rank=r",
                query=title,
            )

            for product in match.get("items", []):
                normalized_authors = get_normalized_authors(product["authors"])
                if (
                    get_normalized_title(product["title"]) != title
                    or not is_matching_authors(target.normalized_authors, normalized_authors)
                ):
                    continue
                try:
                    target.ebook_asin = product["asin"]
                    break
                except KeyError:
                    continue

            return target

    async def get_book(
        self,
        target: Book,
        semaphore: asyncio.Semaphore
    ) -> Union[Book, None]:
        target.exists = False

        if not target.ebook_asin:
            return target

        asin = target.ebook_asin
        async with semaphore:
            for i in range(10):
                match = await self._client.get(
                    f"{self._get_base_url()}/api/bifrost/offers/batch/v1/{asin}?ref_=KindleDeepLinkOffers",
                    headers={"x-client-id": "kindle-android-deeplink"},
                )
                products = match.get("resources", [])
                if not products:
                    await asyncio.sleep(1)
                    continue

                actions = products[0].get("personalizedActionOutput", {}).get("personalizedActions", [])
                if not actions:
                    await asyncio.sleep(1)
                    continue

                for action in actions:
                    if "printListPrice" in action["offer"]:
                        target.list_price = action["offer"]["printListPrice"]["value"]
                        target.current_price = action["offer"]["digitalPrice"]["value"]
                        target.exists = True
                        break

                # The sleep is a pre-emptive backoff
                # Concurrency is already low, but this endpoint loves to throttle
                await asyncio.sleep(.25)
                return target

            return None

    async def get_wishlist(self, config: Config) -> list[Book]:
        """Not currently supported

        Getting this info is proving to be a nightmare

        :param config:
        :return:
        """
        return []

    async def get_library(self, config: Config) -> list[Book]:
        books = []
        pagination_token = 0
        url = f"{self._get_read_base_url()}/kindle-library/search"

        while True:
            optional_params = {}
            if pagination_token:
                optional_params["paginationToken"] = pagination_token

            response = await self._client.get(
                url,
                headers=self._headers,
                query="",
                libraryType="BOOKS",
                sortType="recency",
                resourceType="EBOOK",
                querySize=50,
                **optional_params
            )

            for book in response["itemsList"]:
                books.append(
                    Book(
                        retailer=self.name,
                        title = book["title"],
                        authors = book["authors"][0],
                        format=self.format,
                        timepoint=config.run_time,
                        ebook_asin=book["asin"],
                    )
                )

            if "paginationToken" in response:
                pagination_token = int(response["paginationToken"])
            else:
                break

        return books
