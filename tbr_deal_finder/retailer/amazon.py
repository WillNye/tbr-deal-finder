import sys
import os.path

import audible
import click
from audible.login import build_init_cookies
from textwrap import dedent

if sys.platform != 'win32':
    # Breaks Windows support but required for Mac
    # Untested on Linux
    import readline  # type: ignore

from tbr_deal_finder import TBR_DEALS_PATH
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer.models import Retailer

_AUTH_PATH = TBR_DEALS_PATH.joinpath("audible.json")


def login_url_callback(url: str) -> str:
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
    _auth: audible.Authenticator = None
    _client: audible.AsyncClient = None

    async def set_auth(self):
        if not os.path.exists(_AUTH_PATH):
            auth = audible.Authenticator.from_login_external(
                locale=Config.locale,
                login_url_callback=login_url_callback
            )

            # Save credentials to file
            auth.to_file(_AUTH_PATH)

        self._auth = audible.Authenticator.from_file(_AUTH_PATH)
        self._client = audible.AsyncClient(auth=self._auth)

