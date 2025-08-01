from tbr_deal_finder.book import Book
from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer import RETAILER_MAP
from tbr_deal_finder.retailer.models import Retailer


async def get_owned_books(config: Config) -> list[Book]:
    owned_books = []

    for retailer_str in config.tracked_retailers:
        retailer: Retailer = RETAILER_MAP[retailer_str]()
        await retailer.set_auth()

        owned_books.extend(
            await retailer.get_library(config)
        )

    return owned_books
