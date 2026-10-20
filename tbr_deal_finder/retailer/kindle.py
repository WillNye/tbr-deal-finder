import asyncio
import json
from typing import Union

from audible.exceptions import RatelimitError, ServerError, Unauthorized

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.amazon import Amazon, AUDIBLE_AUTH_PATH
from tbr_deal_finder.book import Book, BookFormat, get_normalized_title, get_normalized_authors, is_matching_authors
from tbr_deal_finder.utils import echo_warning

# Amazon throttles bursts with a 503 "automated access" page (or a 429).
_THROTTLE_ERRORS = (ServerError, RatelimitError)
_THROTTLE_RETRIES = 4
# Amazon doesn't publish its limit, so request starts are spaced by an interval that
# doubles on each throttle and eases back down as requests succeed.
_MIN_REQUEST_INTERVAL = 0.5
_MAX_REQUEST_INTERVAL = 16.0
# The offers endpoint takes comma-separated ASINs; 200 was verified, this keeps headroom.
_OFFERS_BATCH_SIZE = 100
_OFFERS_HEADERS = {"x-client-id": "kindle-android-deeplink"}


class Kindle(Amazon):
    # Class-level so a run's ASIN searches, price checks and library pages share one backoff.
    _request_interval = _MIN_REQUEST_INTERVAL

    def __init__(self):
        self._headers = {}
        # Set once Amazon keeps refusing us, so the rest of the run stops asking.
        self._gave_up = False
        self._pace_lock = asyncio.Lock()
        self._next_request_at = 0.0
        # Searches skipped while throttled (full_title_str), as opposed to books not on Kindle.
        self.skipped_asin_searches: set[str] = set()
        # asin -> offers resource, filled by prefetch.
        self._offers: dict[str, dict] = {}

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

        with open(AUDIBLE_AUTH_PATH, "r") as f:
            auth_info = json.load(f)

            cookies = auth_info["website_cookies"]
            cookies["x-access-token"] = auth_info["access_token"]

        self._headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Kindle) AppleWebKit/537.3",
            "Accept": "application/json, */*",
            "Cookie": "; ".join([f"{k}={v}" for k, v in cookies.items()])
        }


    async def _wait_for_request_slot(self):
        async with self._pace_lock:
            loop = asyncio.get_running_loop()
            delay = self._next_request_at - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            self._next_request_at = loop.time() + Kindle._request_interval

    async def _get(self, url: str, **kwargs) -> dict:
        """Paced GET from Amazon, backing off while it throttles; raises once the retries run out."""
        # Without the login cookies Amazon treats the request as anonymous and intermittently 403s.
        if cookie := self._headers.get("Cookie"):
            kwargs["headers"] = {"Cookie": cookie, **kwargs.get("headers", {})}
        for attempt in range(_THROTTLE_RETRIES):
            await self._wait_for_request_slot()
            try:
                response = await self._client.get(url, **kwargs)
            except _THROTTLE_ERRORS:
                Kindle._request_interval = min(Kindle._request_interval * 2, _MAX_REQUEST_INTERVAL)
                self._next_request_at = asyncio.get_running_loop().time() + Kindle._request_interval
                if attempt == _THROTTLE_RETRIES - 1:
                    raise
                continue

            Kindle._request_interval = max(Kindle._request_interval * 0.9, _MIN_REQUEST_INTERVAL)
            return response

    async def _get_or_skip(self, url: str, **kwargs) -> Union[dict, None]:
        """Like _get, but returns None instead of failing the whole run when Amazon won't answer."""
        if self._gave_up:
            return None
        try:
            return await self._get(url, **kwargs)
        except _THROTTLE_ERRORS:
            self._skip_remaining("Amazon is throttling Kindle requests; skipping the remaining Kindle lookups this run.")
        except Unauthorized:
            self._skip_remaining(
                "Amazon rejected the Kindle session (403); skipping Kindle this run. "
                "If this keeps happening, sign in to Amazon again."
            )
        return None

    def _skip_remaining(self, reason: str):
        if not self._gave_up:
            self._gave_up = True
            echo_warning(reason)

    async def get_book_asin(
        self,
        target: Book,
        semaphore: asyncio.Semaphore
    ) -> Book:
        title = target.title
        async with semaphore:
            match = await self._get_or_skip(
                f"{self._get_base_url()}/kindle-dbs/kws?userCode=AndroidKin&deviceType=A3VNNDO1I14V03&node=2671536011&excludedNodes=&page=1&size=20&autoSpellCheck=1&rank=r",
                query=title,
            )

            if match is None:
                self.skipped_asin_searches.add(target.full_title_str)
                return target

            for product in match.get("items", []):
                normalized_authors = get_normalized_authors(product["authors"])
                if (
                    get_normalized_title(product["title"]) != title
                    or not is_matching_authors(target.normalized_authors, normalized_authors)
                ):
                    continue
                try:
                    target.ebook_asin = product["asin"]
                    # KWS returns only the image filename (iFile); Amazon serves it
                    # from the media CDN. The pricing endpoint carries no cover, so
                    # this search is the only cover source for Kindle ebooks.
                    if i_file := product.get("iFile"):
                        target.image_url = f"https://m.media-amazon.com/images/I/{i_file}"
                    break
                except KeyError:
                    continue

            return target

    def _offers_url(self, asins: list[str]) -> str:
        return f"{self._get_base_url()}/api/bifrost/offers/batch/v1/{','.join(asins)}?ref_=KindleDeepLinkOffers"

    async def prefetch(self, config: Config, books: list[Book]):
        """Fetch offers for every book in batches, so get_book needs no request of its own."""
        asins = sorted({b.ebook_asin for b in books if b.ebook_asin})
        for i in range(0, len(asins), _OFFERS_BATCH_SIZE):
            match = await self._get_or_skip(
                self._offers_url(asins[i:i + _OFFERS_BATCH_SIZE]), headers=_OFFERS_HEADERS
            )
            for resource in (match or {}).get("resources", []):
                self._offers[resource.get("asin")] = resource

    async def _fetch_offer(self, asin: str) -> Union[dict, None]:
        """Single-ASIN fallback for a book the batch didn't return."""
        for _ in range(10):
            match = await self._get_or_skip(self._offers_url([asin]), headers=_OFFERS_HEADERS)
            if match is None:
                return None

            resources = match.get("resources", [])
            if resources and resources[0].get("personalizedActionOutput", {}).get("personalizedActions"):
                return resources[0]
            await asyncio.sleep(1)

        return None

    def _apply_offer(self, target: Book, resource: dict) -> Union[Book, None]:
        actions = (resource.get("personalizedActionOutput") or {}).get("personalizedActions", [])
        if not actions:
            # Nothing to buy or borrow right now; skip rather than mark it unknown.
            return None

        for action in actions:
            offer = action.get("offer") or {}
            if "digitalPrice" in offer:
                target.list_price = self._list_price(offer)
                target.current_price = offer["digitalPrice"]["value"]
                target.exists = True
                target.product_url = f"{self._get_base_url()}/dp/{target.ebook_asin}"
            elif (action.get("actionProgram") or {}).get("programCode") == "KINDLE_UNLIMITED":
                target.alt_price = 0

        return target

    @staticmethod
    def _list_price(offer: dict) -> float:
        """Amazon's fullPrice: the price a sale is discounted from, or the regular price otherwise.

        printListPrice and the savings fields aren't used: they're missing, $0 or below the Kindle
        price for some books, and savingsPercentage doesn't always agree with the prices.
        """
        current = offer["digitalPrice"]["value"]
        return max((offer.get("fullPrice") or {}).get("value") or current, current)

    async def get_book(
        self,
        config: Config,
        target: Book,
        semaphore: asyncio.Semaphore
    ) -> Union[Book, None]:
        target.exists = False

        if not target.ebook_asin:
            return target

        resource = self._offers.get(target.ebook_asin)
        if resource is None:
            async with semaphore:
                resource = await self._fetch_offer(target.ebook_asin)
            if resource is None:
                return None

        return self._apply_offer(target, resource)

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

            # Not skipped when throttled: a partial library would surface owned books as deals.
            response = await self._get(
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
