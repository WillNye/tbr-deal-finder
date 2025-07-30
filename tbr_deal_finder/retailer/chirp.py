import asyncio
from datetime import datetime

import aiohttp

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import Retailer
from tbr_deal_finder.book import Book, BookFormat, get_normalized_authors
from tbr_deal_finder.utils import currency_to_float


class Chirp(Retailer):
    # Static because url for other locales just redirects to .com
    _url: str = "https://www.chirpbooks.com/api/graphql"

    @property
    def name(self) -> str:
        return "Chirp"

    @property
    def format(self) -> BookFormat:
        return BookFormat.AUDIOBOOK

    async def set_auth(self):
        return

    async def get_book(
        self, target: Book, runtime: datetime, semaphore: asyncio.Semaphore
    ) -> Book:
        title = target.title
        authors = target.authors

        async with aiohttp.ClientSession() as http_client:
            response = await http_client.request(
                "POST",
                self._url,
                json={
                    "query": "fragment audiobookFields on Audiobook{id averageRating coverUrl displayAuthors displayTitle ratingsCount url allAuthors{name slug url}} fragment audiobookWithShoppingCartAndUserAudiobookFields on Audiobook{...audiobookFields currentUserShoppingCartItem{id}currentUserWishlistItem{id}currentUserUserAudiobook{id}currentUserHasAuthorFollow{id}} fragment productFields on Product{discountPrice id isFreeListing listingPrice purchaseUrl savingsPercent showListingPrice timeLeft bannerType} query AudiobookSearch($query:String!,$promotionFilter:String,$filter:String,$page:Int,$pageSize:Int){audiobooks(query:$query,promotionFilter:$promotionFilter,filter:$filter,page:$page,pageSize:$pageSize){totalCount objects(page:$page,pageSize:$pageSize){... on Audiobook{...audiobookWithShoppingCartAndUserAudiobookFields futureSaleDate currentProduct{...productFields}}}}}",
                    "variables": {"query": title, "filter": "all", "page": 1, "promotionFilter": "default"},
                    "operationName": "AudiobookSearch"
                }
            )
            response_body = await response.json()
            audiobooks = response_body["data"]["audiobooks"]["objects"]
            if not audiobooks:
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

            for book in audiobooks:
                if not book["currentProduct"]:
                    continue

                if (
                    book["displayTitle"] == title
                    and get_normalized_authors(book["displayAuthors"]) == target.normalized_authors
                ):
                    return Book(
                        retailer=self.name,
                        title=title,
                        authors=authors,
                        list_price=currency_to_float(book["currentProduct"]["listingPrice"]),
                        current_price=currency_to_float(book["currentProduct"]["discountPrice"]),
                        timepoint=runtime,
                        format=BookFormat.AUDIOBOOK,
                    )

            return Book(
                retailer=self.name,
                title=title,
                authors=target.authors,
                list_price=0,
                current_price=0,
                timepoint=runtime,
                format=BookFormat.AUDIOBOOK,
                exists=False,
            )

    async def get_wishlist(self, config: Config) -> list[Book]:
        # TODO: This won't work without logging in user
        # TODO: Add a config to track whether user wants to login to retailers that do not require login
        #   Be sure they're aware they'll lose wishlist tracking and owned book tracking

        wishlist_books = []
        page = 1

        async with aiohttp.ClientSession() as http_client:
            while True:
                http_response = await http_client.request(
                    "POST",
                    self._url,
                    json={
                        "query": "fragment audiobookFields on Audiobook{id averageRating coverUrl displayAuthors displayTitle ratingsCount url allAuthors{name slug url}} fragment productFields on Product{discountPrice id isFreeListing listingPrice purchaseUrl savingsPercent showListingPrice timeLeft bannerType} query FetchWishlistDealAudiobooks($page:Int,$pageSize:Int){currentUserWishlist{paginatedItems(filter:\"currently_promoted\",sort:\"promotion_end_date\",salability:current_or_future){totalCount objects(page:$page,pageSize:$pageSize){... on WishlistItem{id audiobook{...audiobookFields currentProduct{...productFields}}}}}}}",
                        "variables": {"page": page, "pageSize": 15},
                        "operationName": "FetchCurrentUserRelatedAudiobooks"
                    }
                )
                response_body = await http_response.json()
                audiobooks = response_body.get(
                    "data", {}
                ).get("currentUserWishlist", {}).get("paginatedItems", {}).get("objects", [])

                if not audiobooks:
                    print("wut?")
                    print(response_body)
                    return wishlist_books

                for book in audiobooks:
                    audiobook = book["audiobook"]
                    authors = [author["name"] for author in audiobook["displayAuthors"]]
                    wishlist_books.append(
                        Book(
                            retailer=self.name,
                            title=audiobook["displayTitle"],
                            authors=", ".join(authors),
                            list_price=1,
                            current_price=1,
                            timepoint=config.run_time,
                            format=self.format,
                        )
                    )

                page += 1
