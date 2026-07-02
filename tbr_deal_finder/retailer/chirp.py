import asyncio
import base64
import binascii
import json
import os
from datetime import datetime
from textwrap import dedent
from typing import Optional, Union

import click

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import AioHttpSession, Retailer, GuiAuthContext
from tbr_deal_finder.book import Book, BookFormat, get_normalized_authors, is_matching_authors
from tbr_deal_finder.utils import currency_to_float, echo_err


class Chirp(AioHttpSession, Retailer):
    # Static because url for other locales just redirects to .com
    _url: str = "https://api.chirpbooks.com/api/graphql"
    USER_AGENT = "ChirpBooks/5.20.2 (Android)"

    def __init__(self):
        super().__init__()

        self.auth_token = None

    @property
    def name(self) -> str:
        return "Chirp"

    @property
    def format(self) -> BookFormat:
        return BookFormat.AUDIOBOOK

    # GraphQL auth-failure codes Chirp returns. Note these come back with an
    # HTTP 200 status inside an ``errors`` array, not as an HTTP error.
    _AUTH_ERROR_CODES = {"token_invalid", "unauthorized"}

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

    @staticmethod
    def _is_auth_error(response: dict) -> bool:
        """Detect a Chirp authentication failure.

        Chirp returns HTTP 200 with an ``errors`` array (e.g.
        ``{"errors": [{"code": "token_invalid"}]}``) when the bearer token is
        missing, invalid, or expired, so a plain ``response.ok`` check is not
        enough.
        """
        if not response:
            return False
        for error in response.get("errors", []) or []:
            if error.get("code") in Chirp._AUTH_ERROR_CODES:
                return True
        return False

    @staticmethod
    def _token_is_expired(token: str) -> bool:
        """Return True only if the JWT carries an ``exp`` claim that has passed.

        Chirp tokens are JWTs valid for ~1 year. We trust the embedded ``exp``
        rather than a self-imposed window. If the token can't be parsed we
        assume it's still good and let validate-on-use catch a bad token.
        """
        try:
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        except (IndexError, ValueError, binascii.Error):
            return False

        exp = payload.get("exp")
        if not exp:
            return False
        return datetime.now().timestamp() >= exp

    def _load_stored_token(self) -> Optional[str]:
        """Return the stored token if present, regardless of age."""
        if not os.path.exists(self.auth_path):
            return None
        with open(self.auth_path, "r") as f:
            auth_info = json.load(f)
        if not auth_info:
            return None
        try:
            return auth_info["data"]["signIn"]["user"]["token"]
        except (KeyError, TypeError):
            return None

    def user_is_authed(self) -> bool:
        token = self._load_stored_token()
        if not token:
            return False
        if self._token_is_expired(token):
            return False
        # Reuse the stored token indefinitely until it actually expires. If the
        # server has invalidated it early, the next real request surfaces an
        # auth error and triggers a fresh sign-in (see set_auth).
        self.auth_token = token
        return True

    async def token_is_valid(self) -> bool:
        """Confirm the current token still authenticates a real API call."""
        response = await self.make_request(
            "POST",
            json={
                "query": "query AndroidCurrentUserAudiobooks($page: Int!, $pageSize: Int!) { currentUserAudiobooks(page: $page, pageSize: $pageSize, sort: TITLE_A_Z, clientCapabilities: [CHIRP_AUDIO]) { audiobook { id } } }",
                "variables": {"page": 1, "pageSize": 1},
                "operationName": "AndroidCurrentUserAudiobooks",
            }
        )
        return not self._is_auth_error(response)

    async def _sign_in(self, email: str, password: str) -> bool:
        response = await self.make_request(
            "POST",
            json={
                "query": "mutation signIn($email: String!, $password: String!) { signIn(email: $email, password: $password) { user { id token webToken email } } }",
                "variables": {
                    "email": email,
                    "password": password,
                }
            }
        )

        token = response.get("data", {}).get("signIn", {}).get("user", {}).get("token") if response else None
        if not token:
            return False

        # Set token for future requests during the current execution
        self.auth_token = token

        response["created_at"] = datetime.now().timestamp()
        with open(self.auth_path, "w") as f:
            json.dump(response, f)
        return True

    async def set_auth(self):
        # Reuse the persisted token unless it has expired or been revoked.
        if self.user_is_authed() and await self.token_is_valid():
            return

        # Stored token is gone, expired, or rejected by the server: drop it and
        # prompt for a fresh sign-in.
        self.auth_token = None
        if await self._sign_in(
            click.prompt("Chirp account email"),
            click.prompt("Chirp Password", hide_input=True),
        ):
            return

        echo_err("Chirp login failed, please try again.")
        await self.set_auth()

    @property
    def gui_auth_context(self) -> GuiAuthContext:
        return GuiAuthContext(
            title="Login to Chirp",
            fields=[
                {"name": "email", "label": "Email", "type": "email"},
                {"name": "password", "label": "Password", "type": "password"}
            ]
        )

    async def gui_auth(self, form_data: dict) -> bool:
        return await self._sign_in(form_data["email"], form_data["password"])

    async def get_book(
        self, config: Config, target: Book, semaphore: asyncio.Semaphore
    ) -> Union[Book, None]:
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
                    target.image_url = book.get("coverUrl")
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
                        coverUrl
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
                        image_url=audiobook.get("coverUrl"),
                    )
                )

            page += 1
