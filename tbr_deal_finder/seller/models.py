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

    async def get_audio_book(
            self, title: str, authors: str, runtime: datetime, semaphore: asyncio.Semaphore
    ) -> Union[Book, None]:
        """
        Get book information from the provider.
        
        Args:
            title: The book title
            authors: The book authors
            semaphore: Semaphore for rate limiting
            
        Returns:
            Book object if found, None otherwise
            :param title:
            :param authors:
            :param semaphore:
            :param runtime:
        """
        raise NotImplementedError

    async def set_auth(self):
        raise NotImplementedError


