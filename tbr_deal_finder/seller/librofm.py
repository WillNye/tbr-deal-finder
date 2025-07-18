import asyncio
import json
import os
import urllib.parse
from datetime import datetime
from typing import Union

import aiohttp
import click

from tbr_deal_finder import TBR_DEALS_PATH
from tbr_deal_finder.seller.models import Seller
from tbr_deal_finder.book import Book


class LibroFM(Seller):
    BASE_URL = "https://libro.fm"
    USER_AGENT = "okhttp/3.14.9"
    USER_AGENT_DOWNLOAD = (
        "AndroidDownloadManager/11 (Linux; U; Android 11; "
        "Android SDK built for x86_64 Build/RSR1.210722.013.A2)"
    )
    CLIENT_VERSION = (
        "Android: Libro.fm 7.6.1 Build: 194 Device: Android SDK built for x86_64 "
        "(unknown sdk_phone_x86_64) AndroidOS: 11 SDK: 30"
    )

    def __init__(self):
        self.auth_token = None

    @property
    def name(self) -> str:
        return "Libro FM"

    async def make_request(self, url_path: str, request_type: str, **kwargs) -> dict:
        url = urllib.parse.urljoin(self.BASE_URL, url_path)
        headers = kwargs.pop("headers", {})
        headers["User-Agent"] = self.USER_AGENT

        async with aiohttp.ClientSession() as http_client:
            response = await http_client.request(
                request_type.upper(),
                url,
                headers=headers,
                **kwargs
            )
            if response.ok:
                return await response.json()
            else:
                print(response.text)
                return {}

    async def set_auth(self):
        auth_path = TBR_DEALS_PATH.joinpath("libro_fm.json")
        if os.path.exists(auth_path):
            with open(auth_path, "r") as f:
                self.auth_token = json.load(f)["access_token"]

        response = await self.make_request(
            "/oauth/token",
            "POST",
            json={
                "grant_type": "password",
                "username": click.prompt("Libro FM Username"),
                "password": click.prompt("Libro FM Password", hide_input=True),
            }
        )
        self.auth_token = response
        with open(auth_path, "w") as f:
            json.dump(response, f)

    async def get_audio_book(
        self, title: str, authors: str, runtime: datetime, semaphore: asyncio.Semaphore
    ) -> Union[Book, None]:
        # TODO: Move isbn to param
        isbn = "9780063355095"

        response = await self.make_request(
            f"api/v10/explore/audiobook_details/{isbn}",
            "GET"
        )
        # TODO: Parse response and set Book
