import asyncio
from datetime import datetime
from typing import Union

import aiohttp

from tbr_deal_finder.seller.models import Seller
from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.utils import currency_to_float


class Chirp(Seller):
    _url: str = "https://www.chirpbooks.com/api/graphql"

    @property
    def name(self) -> str:
        return "Chirp"

    async def get_audio_book(
        self, title: str, authors: str, runtime: datetime, semaphore: asyncio.Semaphore
    ) -> Union[Book, None]:

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
                print(f"{title} - {authors} - Not Found")
                return None

            for book in audiobooks:
                if not book["currentProduct"]:
                    continue

                if book["displayTitle"] == title and book["displayAuthors"] in authors:
                    return Book(
                        seller=self.name,
                        title=title,
                        authors=authors,
                        list_price=currency_to_float(book["currentProduct"]["listingPrice"]),
                        current_price=currency_to_float(book["currentProduct"]["discountPrice"]),
                        timepoint=runtime,
                        format=BookFormat.AUDIOBOOK,
                    )

            print(f"{title} - {authors} - Not Found")
            return None

    async def set_auth(self):
        return
