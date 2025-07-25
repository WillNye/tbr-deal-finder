import abc
import asyncio
from datetime import datetime

from tbr_deal_finder.book import Book


class Retailer(abc.ABC):
    """Abstract base class for retailers."""

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def get_book(
            self, target: Book, runtime: datetime, semaphore: asyncio.Semaphore
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

    async def set_auth(self):
        raise NotImplementedError


