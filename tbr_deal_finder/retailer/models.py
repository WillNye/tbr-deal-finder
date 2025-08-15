import abc
import asyncio

import aiohttp

from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.config import Config


class Retailer(abc.ABC):
    """Abstract base class for retailers."""

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def format(self) -> BookFormat:
        """The format of the books they sell.

        For example,
        Audible would be audiobooks
        Kindle would be ebooks

        :return:
        """
        raise NotImplementedError

    async def set_auth(self):
        raise NotImplementedError

    async def get_book(
            self, target: Book, semaphore: asyncio.Semaphore
    ) -> Book:
        """Get book information from the retailer.

        - Uses Audible's product API to fetch book details
        - Respects rate limiting through the provided semaphore
        - Returns a Book with exists=False if the book is not found

        Args:
            target: Book object containing search criteria
            runtime: Timestamp for when the search was initiated
            semaphore: Semaphore to control concurrent requests

        Returns:
            Book: Updated book object with pricing and availability
            """
        raise NotImplementedError

    async def get_wishlist(self, config: Config) -> list[Book]:
        raise NotImplementedError

    async def get_library(self, config: Config) -> list[Book]:
        raise NotImplementedError


class AioHttpSession:

    def __init__(self):
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session when done."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        """Support async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on context manager exit."""
        await self.close()

    def __del__(self):
        """Attempt to close session on garbage collection."""
        if self._session and not self._session.closed:
            try:
                asyncio.create_task(self._session.close())
            except RuntimeError:
                # Event loop might be closed
                pass

