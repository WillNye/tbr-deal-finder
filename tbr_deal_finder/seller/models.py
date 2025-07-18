import abc
import asyncio
from datetime import datetime
from typing import Union

from tbr_deal_finder.book import Book


class Seller(abc.ABC):
    """Abstract base class for audio book providers."""

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def get_book(
            self, title: str, authors: str, runtime: datetime, semaphore: asyncio.Semaphore
    ) -> Book:
        """
        Get book information from the provider.
        
        Args:
            title: The book title
            authors: The book authors
            semaphore: Semaphore for rate limiting
            
        Returns:
            Book object, if not found Book.exists will be false
            :param title:
            :param authors:
            :param semaphore:
            :param runtime:
        """
        raise NotImplementedError

    async def set_auth(self):
        raise NotImplementedError


