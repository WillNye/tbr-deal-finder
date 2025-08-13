import asyncio
import copy
from collections import defaultdict

import click
import pandas as pd
from tqdm.asyncio import tqdm_asyncio

from tbr_deal_finder.book import Book, get_active_deals, BookFormat
from tbr_deal_finder.config import Config
from tbr_deal_finder.tracked_books import get_tbr_books
from tbr_deal_finder.retailer import RETAILER_MAP
from tbr_deal_finder.retailer.models import Retailer
from tbr_deal_finder.utils import get_duckdb_conn, echo_warning, echo_info


def update_retailer_deal_table(config: Config, new_deals: list[Book]):
    """Adds new deals to the database and marks old deals as deleted

    :param config:
    :param new_deals:
    """

    # This could be done using a temp table for the new deals, but that feels like overkill.
    # I can't imagine there's ever going to be more than 5,000 books in someone's TBR.
    # If it were any larger, we'd have bigger problems.
    active_deal_map = {deal.deal_id: deal for deal in get_active_deals()}
    # Dirty trick to ensure uniqueness in request
    new_deals = list({nd.deal_id: nd for nd in new_deals}.values())
    df_data = []

    for deal in new_deals:
        if deal.deal_id in active_deal_map:
            if deal.current_price != active_deal_map[deal.deal_id].current_price:
                df_data.append(deal.dict())

            active_deal_map.pop(deal.deal_id)
        else:
            df_data.append(deal.dict())

    # Any remaining values in active_deal_map mean that
    # it wasn't found and should be marked for deletion
    for deal in active_deal_map.values():
        echo_warning(f"{str(deal)} is no longer active\n")
        deal.timepoint = config.run_time
        deal.deleted = True
        df_data.append(deal.dict())

    if df_data:
        df = pd.DataFrame(df_data)

        db_conn = get_duckdb_conn()
        db_conn.register("_df", df)
        db_conn.execute("INSERT INTO retailer_deal SELECT * FROM _df;")
        db_conn.unregister("_df")


async def _get_books(config, retailer: Retailer, books: list[Book]) -> list[Book]:
    """Get Books with limited concurrency.

    - Creates semaphore to limit concurrent requests.
    - Creates a list to store the response.
    - Creates a list to store unresolved books.

     Args:
        config: Application configuration
        retailer: Retailer instance to fetch data from
        books: List of Book objects to look up

    Returns:
        List of Book objects with updated pricing and availability
    """
    semaphore = asyncio.Semaphore(10)
    response = []
    unresolved_books = []
    books = [copy.deepcopy(book) for book in books]
    for book in books:
        book.retailer = retailer.name
        book.format = retailer.format

    tasks = [
        retailer.get_book(book, semaphore)
        for book in books
    ]
    results = await tqdm_asyncio.gather(*tasks, desc=f"Getting latest prices from {retailer.name}")
    for book in results:
        if book.exists:
            response.append(book)
        elif not book.exists:
            unresolved_books.append(book)

    click.echo()
    for book in unresolved_books:
        echo_info(f"{book.title} by {book.authors} not found")

    return response


def _apply_proper_list_prices(books: list[Book]):
    """
    Applies the lowest list price found across all retailers to each book.

    This function:
    - Creates a mapping of book titles and authors to their list prices.
    - For each book, it checks if the list price is higher than the current value.
    - If the list price is higher, it updates the book's list price.
    """

    book_pricing_map = defaultdict(dict)
    for book in books:
        relevant_book_map = book_pricing_map[book.title_id]

        if book.list_price > 0 and (
            "list_price" not in relevant_book_map
            or relevant_book_map["list_price"] > book.list_price
        ):
            relevant_book_map["list_price"] = book.list_price

        if "retailers" not in relevant_book_map:
            relevant_book_map["retailers"] = []

        relevant_book_map["retailers"].append(book)

    # Apply the lowest list price to all
    for book_info in book_pricing_map.values():
        list_price = book_info.get("list_price", 0)
        for book in book_info["retailers"]:
            # Using current_price if list_price couldn't be determined,
            # This is an issue with Libro.fm where it doesn't return list price
            book.list_price = max(book.current_price, list_price)


def _get_retailer_relevant_tbr_books(
    retailer: Retailer,
    books: list[Book],
) -> list[Book]:
    """
    Don't check on deals in a specified format that does not match the format the retailer sells.

    :param retailer:
    :param books:
    :return:
    """

    response = []

    for book in books:
        if book.format == BookFormat.NA or book.format == retailer.format:
            response.append(book)

    return response


async def get_latest_deals(config: Config):
    """
    Fetches the latest book deals from all tracked retailers for the user's TBR list.

    This function:
    - Retrieves the user's TBR books based on the provided config.
    - Iterates through each retailer specified in the config.
    - For each retailer, fetches the latest deals for the TBR books, handling authentication as needed.
    - Applies the lowest list price found across all retailers to each book.
    - Filters books to those that meet the user's max price and minimum discount requirements.
    - Updates the retailer deal table with the filtered deals.

    Args:
        config (Config): The user's configuration object.

    """

    books: list[Book] = []
    tbr_books = await get_tbr_books(config)

    for retailer_str in config.tracked_retailers:
        retailer = RETAILER_MAP[retailer_str]()
        await retailer.set_auth()

        relevant_tbr_books = _get_retailer_relevant_tbr_books(
            retailer,
            tbr_books,
        )

        echo_info(f"Getting deals from {retailer.name}")
        click.echo("\n---------------")
        books.extend(await _get_books(config, retailer, relevant_tbr_books))
        click.echo("---------------\n")

    _apply_proper_list_prices(books)

    books = [
        book
        for book in books
        if book.current_price <= config.max_price and book.discount() >= config.min_discount
    ]

    update_retailer_deal_table(config, books)
