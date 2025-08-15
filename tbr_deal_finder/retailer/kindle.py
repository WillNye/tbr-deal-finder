import asyncio
import readline  # type: ignore

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.amazon import Amazon
from tbr_deal_finder.book import Book, BookFormat, get_normalized_title, get_normalized_authors, is_matching_authors


class Kindle(Amazon):

    @property
    def name(self) -> str:
        return "Kindle"

    @property
    def format(self) -> BookFormat:
        return BookFormat.EBOOK

    def _get_base_url(self) -> str:
        return f"https://www.amazon.{self._auth.locale.domain}"

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
    ) -> Book:
        target.exists = False

        if not target.ebook_asin:
            return target

        asin = target.ebook_asin
        async with semaphore:
            match = await self._client.get(
                f"{self._get_base_url()}/api/bifrost/offers/batch/v1/{asin}?ref_=KindleDeepLinkOffers",
                headers={"x-client-id": "kindle-android-deeplink"},
            )
            products = match.get("resources", [])
            if not products:
                return target

            actions = products[0].get("personalizedActionOutput", {}).get("personalizedActions", [])
            if not actions:
                return target

            for action in actions:
                if "printListPrice" in action["offer"]:
                    target.list_price = action["offer"]["printListPrice"]["value"]
                    target.current_price = action["offer"]["digitalPrice"]["value"]
                    target.exists = True
                    break

            return target

    async def get_wishlist(self, config: Config) -> list[Book]:
        """Not currently supported

        Getting this info is proving to be a nightmare

        :param config:
        :return:
        """
        return []

    async def get_library(self, config: Config) -> list[Book]:
        """Not currently supported

        Getting this info is proving to be a nightmare

        :param config:
        :return:
        """
        return []

    async def _get_library_attempt(self, config: Config) -> list[Book]:
        """This should work, but it's returning a redirect

        The user is already authenticated at this point, so I'm not sure what's happening
        """
        response = []
        pagination_token = 0
        total_pages = 1

        while pagination_token < total_pages:
            optional_params = {}
            if pagination_token:
                optional_params["paginationToken"] = pagination_token

            response = await self._client.get(
                "https://read.amazon.com/kindle-library/search",
                query="",
                libraryType="BOOKS",
                sortType="recency",
                resourceType="EBOOK",
                querySize=5,
                **optional_params
            )

            if "paginationToken" in response:
                total_pages = int(response["paginationToken"])

            for book in response["itemsList"]:
                response.append(
                    Book(
                        retailer=self.name,
                        title = book["title"],
                        authors = book["authors"][0],
                        format=self.format,
                        timepoint=config.run_time,
                        ebook_asin=book["asin"],
                    )
                )

        return response
