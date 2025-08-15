import asyncio
import math

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.amazon import Amazon
from tbr_deal_finder.book import Book, BookFormat, get_normalized_title


class Audible(Amazon):

    @property
    def name(self) -> str:
        return "Audible"

    @property
    def format(self) -> BookFormat:
        return BookFormat.AUDIOBOOK

    async def get_book(
        self,
        target: Book,
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
                if get_normalized_title(product["title"]) != title:
                    continue
                try:
                    target.list_price = product["price"]["list_price"]["base"]
                    target.current_price = product["price"]["lowest_price"]["base"]
                    target.exists = True
                    return target
                except KeyError:
                    continue

            target.exists = False
            return target

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
