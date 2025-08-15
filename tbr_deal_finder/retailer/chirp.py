import asyncio
import json
import os
from datetime import datetime, timedelta
from textwrap import dedent

import aiohttp
import click

from tbr_deal_finder import TBR_DEALS_PATH
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import AioHttpSession, Retailer
from tbr_deal_finder.book import Book, BookFormat, get_normalized_authors, is_matching_authors
from tbr_deal_finder.utils import currency_to_float, echo_err


class Chirp(AioHttpSession, Retailer):
    # Static because url for other locales just redirects to .com
    _url: str = "https://api.chirpbooks.com/api/graphql"
    USER_AGENT = "ChirpBooks/5.13.9 (Android)"

    def __init__(self):
        super().__init__()

        self.auth_token = None

    @property
    def name(self) -> str:
        return "Chirp"

    @property
    def format(self) -> BookFormat:
        return BookFormat.AUDIOBOOK

    async def make_request(self, request_type: str, **kwargs) -> dict:
        headers = kwargs.pop("headers", {})
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = self.USER_AGENT
        if self.auth_token:
            headers["authorization"] = f"Bearer {self.auth_token}"

        session = await self._get_session()
        response = await session.request(
            request_type.upper(),
            self._url,
            headers=headers,
            **kwargs
        )
        if response.ok:
            return await response.json()
        else:
            return {}

    async def set_auth(self):
        auth_path = TBR_DEALS_PATH.joinpath("chirp.json")
        if os.path.exists(auth_path):
            with open(auth_path, "r") as f:
                auth_info = json.load(f)
                if auth_info:
                    token_created_at = datetime.fromtimestamp(auth_info["created_at"])
                    max_token_age = datetime.now() - timedelta(days=5)
                    if token_created_at > max_token_age:
                        self.auth_token = auth_info["data"]["signIn"]["user"]["token"]
                        return

        response = await self.make_request(
            "POST",
            json={
                "query": "mutation signIn($email: String!, $password: String!) { signIn(email: $email, password: $password) { user { id token webToken email } } }",
                "variables": {
                    "email": click.prompt("Chirp account email"),
                    "password": click.prompt("Chirp Password", hide_input=True),
                }
            }
        )
        if not response:
            echo_err("Chirp login failed, please try again.")
            await self.set_auth()

        # Set token for future requests during the current execution
        self.auth_token = response["data"]["signIn"]["user"]["token"]

        response["created_at"] = datetime.now().timestamp()
        with open(auth_path, "w") as f:
            json.dump(response, f)

    async def get_book(
        self, target: Book, semaphore: asyncio.Semaphore
    ) -> Book:
        title = target.title
        async with semaphore:
            session = await self._get_session()
            response = await session.request(
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
                target.exists = False
                return target

            for book in audiobooks:
                if not book["currentProduct"]:
                    continue

                normalized_authors = get_normalized_authors([author["name"] for author in book["allAuthors"]])
                if (
                    book["displayTitle"] == title
                    and is_matching_authors(target.normalized_authors, normalized_authors)
                ):
                    target.list_price = currency_to_float(book["currentProduct"]["listingPrice"])
                    target.current_price = currency_to_float(book["currentProduct"]["discountPrice"])
                    return target

            target.exists = False
            return target

    async def get_wishlist(self, config: Config) -> list[Book]:
        wishlist_books = []
        page = 1

        while True:
            response = await self.make_request(
                "POST",
                json={
                    "query": "fragment audiobookFields on Audiobook{id averageRating coverUrl displayAuthors displayTitle ratingsCount url allAuthors{name slug url}} fragment productFields on Product{discountPrice id isFreeListing listingPrice purchaseUrl savingsPercent showListingPrice timeLeft bannerType} query FetchWishlistDealAudiobooks($page:Int,$pageSize:Int){currentUserWishlist{paginatedItems(filter:\"currently_promoted\",sort:\"promotion_end_date\",salability:current_or_future){totalCount objects(page:$page,pageSize:$pageSize){... on WishlistItem{id audiobook{...audiobookFields currentProduct{...productFields}}}}}}}",
                    "variables": {"page": page, "pageSize": 15},
                    "operationName": "FetchWishlistDealAudiobooks"
                }
            )

            audiobooks = response.get(
                "data", {}
            ).get("currentUserWishlist", {}).get("paginatedItems", {}).get("objects", [])

            if not audiobooks:
                return wishlist_books

            for book in audiobooks:
                audiobook = book["audiobook"]
                authors = [author["name"] for author in audiobook["allAuthors"]]
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

    async def get_library(self, config: Config) -> list[Book]:
        library_books = []
        page = 1
        query = dedent("""
            query AndroidCurrentUserAudiobooks($page: Int!, $pageSize: Int!) {
                currentUserAudiobooks(page: $page, pageSize: $pageSize, sort: TITLE_A_Z, clientCapabilities: [CHIRP_AUDIO]) {
                    audiobook {
                        id
                        allAuthors{name}
                        displayTitle
                        displayAuthors
                        displayNarrators
                        durationMs
                        description
                        publisher
                    }
                    archived
                    playable
                    finishedAt
                    currentOverallOffsetMs
                }
            }
        """)

        while True:
            response = await self.make_request(
                "POST",
                json={
                    "query": query,
                    "variables": {"page": page, "pageSize": 15},
                    "operationName": "AndroidCurrentUserAudiobooks"
                }
            )

            audiobooks = response.get(
                "data", {}
            ).get("currentUserAudiobooks", [])

            if not audiobooks:
                return library_books

            for book in audiobooks:
                audiobook = book["audiobook"]
                authors = [author["name"] for author in audiobook["allAuthors"]]
                library_books.append(
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
