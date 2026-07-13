import asyncio
import base64
import html
import json
import logging
import os
import re
import secrets
import string
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent
from typing import Optional, Union

import aiohttp
import click
import requests

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import AioHttpSession, Retailer, GuiAuthContext
from tbr_deal_finder.book import (
    Book,
    BookFormat,
    get_normalized_authors,
    get_normalized_title,
    is_matching_authors,
)
from tbr_deal_finder.utils import echo_err, get_data_dir

logger = logging.getLogger(__name__)


def _kobo_cover_url(image_id) -> str:
    """Build a Kobo cover URL from an ImageId.

    Kobo returns only an ImageId; covers are served from a stable CDN template.
    The plain form yields the full-resolution cover.
    """
    return f"https://cdn.kobo.com/book-images/{image_id}/image.jpg"


# Kobo storefront path segments per app locale. Only locales whose
# {country}/{lang} are browser-verified are included; anything else yields no
# URL (button hidden) rather than a guessed link that could 404.
_KOBO_LOCALE_PATH = {
    "us": ("us", "en"),
    "ca": ("ca", "en"),
    "au": ("au", "en"),
    "de": ("de", "de"),
    "fr": ("fr", "fr"),
    "it": ("it", "it"),
    "es": ("es", "es"),
    "in": ("in", "en"),
    # Deliberately omitted (unverified): uk (gb?), jp, br.
}


def _kobo_store_url(store_type: str, slug: Optional[str]) -> Optional[str]:
    """Build a Kobo storefront URL from the API's Slug (used verbatim, trailing
    int included). Returns None for unconfident locales or a missing slug."""
    path = _KOBO_LOCALE_PATH.get(Config.locale)
    if not path or not slug:
        return None
    country, lang = path
    return f"https://www.kobo.com/{country}/{lang}/{store_type}/{slug}"


class KoboEbook(AioHttpSession, Retailer):
    STORE_API = "https://storeapi.kobo.com"
    AUTH_HOST = "https://auth.kobobooks.com"
    AFFILIATE = "Kobo"
    # Pair as the Android app (PlatformId ...4000), NOT a Kobo Touch e-reader
    # (...0373). This is load-bearing: Kobo scopes catalog search by the paired
    # platform's capabilities, and an e-reader can't play audio, so an e-reader
    # pairing returns ZERO audiobooks from /v1/products & /v2/products search
    # (while still allowing audiobook access by-id / via wishlist+library).
    # Pairing as Android is what makes audiobook search/pricing work.
    APP_VERSION = "10.8.2.39915"
    PLATFORM_ID = "00000000-0000-0000-0000-000000004000"
    DISPLAY_PROFILE = "Android"
    DEVICE_OS = "Android"
    DEVICE_OS_VERSION = "34"
    USER_AGENT = (
        "Mozilla/5.0 (Linux; U; Android 2.0; en-us;) AppleWebKit/538.1 "
        "(KHTML, like Gecko) Version/4.0 Mobile Safari/538.1 "
        "(Kobo Touch 0373/4.38.23171)"
    )
    TOKEN_TTL = timedelta(days=14)
    _entitlement_key = "BookMetadata"
    _product_metadata_key = "Book"
    # `typesToInclude` value the /v1/products search filters on. Mirrors the
    # official client's ProductSearchType ("book" / "audiobook").
    _search_type = "book"
    store_type = "ebook"

    def __init__(self):
        super().__init__()
        self.device_id: Optional[str] = None
        self.serial_number: Optional[str] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_key: Optional[str] = None
        self.user_id: Optional[str] = None
        self.user_email: Optional[str] = None

        # Cached activation state (populated by gui_auth_context, consumed by gui_auth).
        self._activation_poll_url: Optional[str] = None
        self._activation_start_url: Optional[str] = None
        self._activation_code: Optional[str] = None

    @property
    def name(self) -> str:
        return "Kobo E-Book"

    @property
    def format(self) -> BookFormat:
        return BookFormat.EBOOK

    @property
    def auth_path(self) -> Path:
        return get_data_dir().joinpath("kobo.json")

    @staticmethod
    def _random_hex(length: int) -> str:
        return "".join(secrets.choice(string.hexdigits) for _ in range(length)).lower()

    def _client_key(self) -> str:
        return base64.b64encode(self.PLATFORM_ID.encode()).decode()

    def _ensure_device_identity(self) -> None:
        if not self.device_id:
            self.device_id = self._random_hex(64)
        if not self.serial_number:
            self.serial_number = self._random_hex(32)

    def _load_persisted(self) -> dict:
        if not os.path.exists(self.auth_path):
            return {}
        try:
            with open(self.auth_path, "r") as f:
                return json.load(f) or {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _persist(self) -> None:
        payload = {
            "created_at": datetime.now().timestamp(),
            "DeviceId": self.device_id,
            "SerialNumber": self.serial_number,
            "AccessToken": self.access_token,
            "RefreshToken": self.refresh_token,
            "UserKey": self.user_key,
            "UserId": self.user_id,
            "UserEmail": self.user_email,
        }
        with open(self.auth_path, "w") as f:
            json.dump(payload, f)

    def user_is_authed(self) -> bool:
        data = self._load_persisted()
        if not data:
            return False

        # Always carry forward a persisted device identity so we don't
        # re-pair on every login.
        self.device_id = data.get("DeviceId") or self.device_id
        self.serial_number = data.get("SerialNumber") or self.serial_number
        self.refresh_token = data.get("RefreshToken") or self.refresh_token

        access_token = data.get("AccessToken")
        if not access_token or not data.get("UserKey"):
            return False

        # A refresh token lets us renew the access token silently — lazily on
        # 401 (see _store_response) — so the session stays valid indefinitely
        # and we never force a full browser re-pair on token age. Only fall
        # back to the TTL when there's no refresh token to lean on (parity with
        # Libro/Chirp, which don't issue one).
        if not self.refresh_token:
            created_at = datetime.fromtimestamp(data.get("created_at", 0))
            if datetime.now() - created_at > self.TOKEN_TTL:
                return False

        self.access_token = access_token
        self.user_key = data.get("UserKey")
        self.user_id = data.get("UserId")
        self.user_email = data.get("UserEmail")
        return True

    def _activate_on_web(self) -> tuple[str, str, str]:
        self._ensure_device_identity()

        params = {
            "pwspid": self.PLATFORM_ID,
            "wsa": self.AFFILIATE,
            "pwsdid": self.device_id,
            "pwsav": self.APP_VERSION,
            "pwsdm": self.PLATFORM_ID,
            "pwspos": self.DEVICE_OS,
            "pwspov": self.DEVICE_OS_VERSION,
        }
        resp = requests.get(
            f"{self.AUTH_HOST}/ActivateOnWeb",
            params=params,
            headers={"User-Agent": self.USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.text

        poll_match = re.search(r'data-poll-endpoint="([^"]+)"', body)
        if not poll_match:
            raise RuntimeError(
                "Kobo activation page didn't include a poll endpoint — Kobo may have changed the page format."
            )
        poll_url = f"{self.AUTH_HOST}{html.unescape(poll_match.group(1))}"

        start_match = re.search(
            r"qrcodegenerator/generate\?url=([^\"'&]+)", body
        )
        code_match = re.search(
            r"qrcodegenerator/generate.+?%26code%3D(\d+)", body
        )
        if not start_match or not code_match:
            raise RuntimeError(
                "Kobo activation page didn't include the activation URL — Kobo may have changed the page format."
            )
        start_url = urllib.parse.unquote(start_match.group(1))
        code = code_match.group(1)

        return poll_url, start_url, code

    async def _poll_activation(self, poll_url: str) -> Optional[dict]:
        """One activation-status poll. Returns activation payload on completion,
        None if still pending.
        """
        session = await self._get_session()
        resp = await session.post(
            poll_url, headers={"User-Agent": self.USER_AGENT}
        )
        if not resp.ok:
            return None
        try:
            data = await resp.json(content_type=None)
        except Exception:
            return None
        if data.get("Status") != "Complete":
            return None

        redirect_url = data.get("RedirectUrl", "")
        parsed = urllib.parse.urlparse(redirect_url)
        qs = urllib.parse.parse_qs(parsed.query)

        try:
            return {
                "UserKey": qs["userKey"][0],
                "UserId": qs["userId"][0],
                "UserEmail": qs["email"][0],
            }
        except KeyError:
            return None

    async def _authenticate_device(self) -> bool:
        self._ensure_device_identity()
        post_data = {
            "AffiliateName": self.AFFILIATE,
            "AppVersion": self.APP_VERSION,
            "ClientKey": self._client_key(),
            "DeviceId": self.device_id,
            "PlatformId": self.PLATFORM_ID,
            "SerialNumber": self.serial_number,
        }
        if self.user_key:
            post_data["UserKey"] = self.user_key

        session = await self._get_session()
        resp = await session.post(
            f"{self.STORE_API}/v1/auth/device",
            json=post_data,
            headers={"User-Agent": self.USER_AGENT},
        )
        if not resp.ok:
            return False
        data = await resp.json()
        if data.get("TokenType") != "Bearer":
            return False

        self.access_token = data["AccessToken"]
        self.refresh_token = data.get("RefreshToken")
        if self.user_key and data.get("UserKey"):
            self.user_key = data["UserKey"]
        return True

    async def _refresh_access_token(self) -> bool:
        if not self.refresh_token:
            return False
        post_data = {
            "AppVersion": self.APP_VERSION,
            "ClientKey": self._client_key(),
            "PlatformId": self.PLATFORM_ID,
            "RefreshToken": self.refresh_token,
        }
        session = await self._get_session()
        resp = await session.post(
            f"{self.STORE_API}/v1/auth/refresh",
            json=post_data,
            headers={
                "User-Agent": self.USER_AGENT,
                "Authorization": f"Bearer {self.access_token}" if self.access_token else "",
            },
        )
        if not resp.ok:
            return False
        data = await resp.json()
        if data.get("TokenType") != "Bearer":
            return False
        self.access_token = data["AccessToken"]
        self.refresh_token = data.get("RefreshToken") or self.refresh_token
        self._persist()
        return True

    @property
    def gui_auth_context(self) -> GuiAuthContext:
        if not self.device_id:
            persisted = self._load_persisted()
            self.device_id = persisted.get("DeviceId")
            self.serial_number = persisted.get("SerialNumber")

        try:
            poll_url, start_url, code = self._activate_on_web()
        except Exception as e:
            logger.info("Kobo ActivateOnWeb failed: %s", e)
            return GuiAuthContext(
                title="Login to Kobo",
                fields=[],
                message=(
                    "Couldn't reach Kobo's activation service. Check your "
                    "network connection and try again.\n\n"
                    f"({e})"
                ),
                pop_up_type="message",
            )

        self._activation_poll_url = poll_url
        self._activation_start_url = start_url
        self._activation_code = code

        message = dedent(
            f"""
            Sign in to Kobo by pairing this app with your account — the same
            way you'd pair a smart-TV app:

            1) "Copy" the Kobo activation link below.
            2) Paste it in the browser of your choice.
            3) If Kobo asks, confirm the activation code: {code}
            4) After you login, this pop-up will close automatically.
            """
        ).strip()

        return GuiAuthContext(
            title="Login to Kobo",
            fields=[],
            message=message,
            user_copy_context=start_url,
            pop_up_type="form",
            auto_poll=True,
        )

    async def gui_auth(self, form_data: dict) -> bool:
        if not self._activation_poll_url:
            return False

        result = await self._poll_activation(self._activation_poll_url)
        if not result:
            return False

        self.user_key = result["UserKey"]
        self.user_id = result["UserId"]
        self.user_email = result["UserEmail"]
        if await self._authenticate_device():
            self._persist()
            return True
        return False

    async def set_auth(self):
        if self.user_is_authed():
            return

        # Try a silent refresh first.
        if self.refresh_token and await self._refresh_access_token():
            return

        try:
            poll_url, start_url, code = self._activate_on_web()
        except Exception as e:
            echo_err(f"Failed to start Kobo activation: {e}")
            return

        self._activation_poll_url = poll_url
        self._activation_start_url = start_url
        self._activation_code = code

        click.echo(
            dedent(
                f"""
                To finish signing into Kobo, open this URL in any browser:

                    {start_url}

                Sign in (Google, Facebook, Apple, or Kobo email all work),
                then confirm the activation code when prompted:

                    {code}

                We'll wait here and complete pairing as soon as Kobo says
                you've activated.
                """
            ).strip()
        )

        # Poll forever (5s intervals) until the user finishes or Ctrl-Cs.
        while True:
            result = await self._poll_activation(poll_url)
            if result:
                self.user_key = result["UserKey"]
                self.user_id = result["UserId"]
                self.user_email = result["UserEmail"]
                break
            await asyncio.sleep(5)

        if not await self._authenticate_device():
            echo_err("Kobo device pairing failed after activation. Please try again.")
            return

        self._persist()
        click.echo("Kobo login complete.")

    def _kobo_headers(self) -> dict:
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def _store_response(
        self,
        path: str,
        params: Optional[dict] = None,
        method: str = "GET",
        extra_headers: Optional[dict] = None,
    ) -> aiohttp.ClientResponse:
        session = await self._get_session()
        url = path if path.startswith("http") else f"{self.STORE_API}{path}"

        def headers() -> dict:
            h = self._kobo_headers()
            if extra_headers:
                h.update(extra_headers)
            return h

        resp = await session.request(
            method.upper(), url, params=params, headers=headers()
        )
        if resp.status == 401 and await self._refresh_access_token():
            resp = await session.request(
                method.upper(), url, params=params, headers=headers()
            )
        return resp

    async def _store_request(
        self,
        path: str,
        params: Optional[dict] = None,
        method: str = "GET",
    ) -> dict:
        resp = await self._store_response(path, params=params, method=method)
        if not resp.ok:
            return {}
        try:
            return await resp.json()
        except Exception:
            return {}

    @staticmethod
    def _author_names(contributors) -> list[str]:
        if not contributors:
            return []
        if isinstance(contributors, str):
            # Real responses send Contributors as a single comma-separated string.
            return [c.strip() for c in contributors.split(",") if c.strip()]
        names = []
        for c in contributors:
            if isinstance(c, dict):
                name = c.get("Name") or c.get("name")
                if name:
                    names.append(name)
            elif isinstance(c, str):
                names.append(c)
        return names

    @staticmethod
    def _kobo_member_price(product: dict, current_price: float) -> Optional[float]:
        # Included in a Kobo subscription (Kobo Plus) -> free while subscribed.
        if product.get("ApplicableSubscriptions"):
            return 0.0

        love = product.get("ActiveLovePrice") or product.get("LovePrice")
        if isinstance(love, dict):
            love = love.get("Price")
        if love is None:
            return None
        try:
            love = float(love)
        except (TypeError, ValueError):
            return None
        return love if love < current_price else None

    async def get_book(
        self,
        config: Config,
        target: Book,
        semaphore: asyncio.Semaphore,
    ) -> Union[Book, None]:
        title = target.title

        async with semaphore:
            response = await self._store_request(
                "/v1/products",
                params={
                    "q": title,
                    "typesToInclude": self._search_type,
                    "pageindex": 0,
                    "pagesize": 20,
                },
            )

            items = response.get("Items") or []
            if not items:
                target.exists = False
                return target

            for item in items:
                book = item.get(self._product_metadata_key) or {}
                product_title = book.get("Title")
                if not product_title:
                    continue
                if get_normalized_title(product_title) != title:
                    continue

                author_names = self._author_names(book.get("Contributors"))
                if not is_matching_authors(
                    target.normalized_authors, get_normalized_authors(author_names)
                ):
                    continue

                price = book.get("Price") or {}
                current = price.get("Price")
                if current is None:
                    continue

                current = float(current)

                if list_price := book.get("WasPrice"):
                    target.list_price = float(list_price)
                else:
                    target.list_price = current

                if book.get("IsFree"):
                    target.current_price = 0.0
                else:
                    target.current_price = current

                # Capture the Kobo Plus / Kobo Love member price (applied only
                # for members in retailer_deal._apply_proper_current_price_kobo).
                member_price = self._kobo_member_price(book, target.current_price)
                if member_price is not None:
                    target.alt_price = member_price

                if image_id := book.get("ImageId"):
                    target.image_url = _kobo_cover_url(image_id)

                target.product_url = _kobo_store_url(self.store_type, book.get("Slug"))

                target.exists = True
                return target

            target.exists = False
            return target

    def _book_from_product_dict(
        self,
        config: Config,
        product: Optional[dict]
    ) -> Optional[Book]:
        if not product:
            return None

        member_price = None
        price = product.get("Price") or {}
        current_price = price.get("Price")
        if current_price:
            current_price = float(current_price)

            if list_price := product.get("WasPrice"):
                list_price = float(list_price)
            else:
                list_price = current_price

            if product.get("IsFree"):
                current_price = 0.0

            member_price = self._kobo_member_price(product, current_price)
        else:
            list_price = 1
            current_price = 1

        title = product.get("Title")
        if not title:
            return None
        authors = self._author_names(
            product.get("Contributors") or product.get("ContributorRoles")
        )
        book = Book(
            retailer=self.name,
            title=title,
            authors=", ".join(authors),
            list_price=list_price,
            current_price=current_price,
            timepoint=config.run_time,
            format=self.format,
        )
        if member_price is not None:
            book.alt_price = member_price
        if image_id := product.get("ImageId"):
            book.image_url = _kobo_cover_url(image_id)
        return book

    async def get_wishlist(self, config: Config) -> list[Book]:
        books: list[Book] = []

        page_index = 0
        while True:
            response = await self._store_request(
                "/v1/user/wishlist",
                params={"PageIndex": page_index, "PageSize": 100},
            )
            items = response.get("Items") or []
            for item in items:
                book = self._book_from_product_dict(
                    config,
                    (item.get("ProductMetadata") or {}).get(self._product_metadata_key)
                )
                if book:
                    books.append(book)

            total_pages = response.get("TotalPageCount") or 1
            page_index += 1
            if not items or page_index >= total_pages:
                break

        return books

    async def get_library(self, config: Config) -> list[Book]:
        books: list[Book] = []

        sync_token = ""
        # Kobo signals more pages via the `x-kobo-sync: continue` response
        # header and hands back the next cursor in `x-kobo-synctoken`. Cap the
        # loop so a misbehaving cursor can't spin forever.
        for _ in range(100):
            resp = await self._store_response(
                "/v1/library/sync",
                params={"DownloadUrlFilter": "Generic", "PrioritizeRecentReads": "false"},
                extra_headers={"x-kobo-synctoken": sync_token},
            )
            if not resp.ok:
                break
            try:
                entries = await resp.json(content_type=None)
            except Exception:
                break

            for entry in entries or []:

                entitlement = entry.get("NewEntitlement") or entry.get("ChangedEntitlement")
                if not entitlement:
                    continue
                book = self._book_from_product_dict(
                    config,
                    entitlement.get(self._entitlement_key)
                )
                if book:
                    books.append(book)

            sync_token = resp.headers.get("x-kobo-synctoken", "")
            if resp.headers.get("x-kobo-sync", "").lower() != "continue":
                break

        return books


class KoboAudiobook(KoboEbook):
    _entitlement_key = "AudiobookMetadata"
    _product_metadata_key = "Audiobook"
    _search_type = "audiobook"
    store_type = "audiobook"

    @property
    def name(self) -> str:
        return "Kobo Audiobook"

    @property
    def format(self) -> BookFormat:
        return BookFormat.AUDIOBOOK
