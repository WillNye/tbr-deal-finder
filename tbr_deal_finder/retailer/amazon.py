import logging
import sys
import os.path
from typing import Union

import audible
import click
from audible.login import build_init_cookies
from textwrap import dedent

from tbr_deal_finder.retailer.amazon_custom_auth import CustomAuthenticator
from tbr_deal_finder.utils import get_data_dir

if sys.platform != 'win32':
    # Breaks Windows support but required for Mac
    # Untested on Linux
    import readline  # type: ignore

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import Retailer, GuiAuthContext

AUTH_PATH = get_data_dir().joinpath("audible.json")

logger = logging.getLogger(__name__)


def default_login_url_callback(url: str) -> str:
    """Helper function for login with external browsers."""

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        pass
    else:
        with sync_playwright() as p:
            iphone = p.devices["iPhone 12 Pro"]
            browser = p.webkit.launch(headless=False)
            context = browser.new_context(
                **iphone
            )
            cookies = []
            for name, value in build_init_cookies().items():
                cookies.append(
                    {
                        "name": name,
                        "value": value,
                        "url": url
                    }
                )
            context.add_cookies(cookies)
            page = browser.new_page()
            page.goto(url)

            while True:
                page.wait_for_timeout(600)
                if "/ap/maplanding" in page.url:
                    response_url = page.url
                    break

            browser.close()
        return response_url

    message = f"""\
        Please copy the following url and insert it into a web browser of your choice to log into Amazon.
        Note: your browser will show you an error page (Page not found). This is expected.
        
        {url}

        Once you have logged in, please insert the copied url.
    """
    click.echo(dedent(message))
    return input()


class Amazon(Retailer):
    _auth: Union[audible.Authenticator, CustomAuthenticator] = None
    _client: audible.AsyncClient = None

    def user_is_authed(self) -> bool:
        if not os.path.exists(AUTH_PATH):
            return False

        self._auth = audible.Authenticator.from_file(AUTH_PATH)
        self._client = audible.AsyncClient(auth=self._auth)
        return True

    async def set_auth(self):
        if not self.user_is_authed():
            auth = audible.Authenticator.from_login_external(
                locale=Config.locale,
                login_url_callback=default_login_url_callback
            )

            # Save credentials to file
            auth.to_file(AUTH_PATH)

        self._auth = audible.Authenticator.from_file(AUTH_PATH)
        self._client = audible.AsyncClient(auth=self._auth)

    @property
    def gui_auth_context(self) -> GuiAuthContext:
        if not self._auth:
            self._auth = CustomAuthenticator.from_locale(Config.locale)

        return GuiAuthContext(
            title="Login to Amazon (Audible/Kindle)",
            fields=[
                {"name": "login_link", "label": "Link", "type": "text"}
            ],
            message=dedent(
                """
                Please copy the following url and insert it into a web browser of your choice to log into Amazon.
                Once you have logged in, please insert the copied url.
                Note: your browser will show you an error page (Page not found). This is expected.
                """
            ),
            user_copy_context=self._auth.oauth_url
        )


    async def gui_auth(self, form_data: dict) -> bool:
        if not self._auth:
            if self.user_is_authed():
                return True
        try:
            self._auth.external_login(form_data["login_link"])
            # Save credentials to file
            self._auth.to_file(AUTH_PATH)

            self._auth = audible.Authenticator.from_file(AUTH_PATH)
            self._client = audible.AsyncClient(auth=self._auth)
            return True
        except Exception as e:
            logger.info(e)
            return False

