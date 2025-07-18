import asyncio
import csv

import pandas as pd
from tqdm.asyncio import tqdm_asyncio

from tbr_deal_finder.book import Book, get_active_deals
from tbr_deal_finder.config import Config
from tbr_deal_finder.seller.audible import Audible
from tbr_deal_finder.seller.chirp import Chirp
from tbr_deal_finder.seller.models import Seller
from tbr_deal_finder.utils import get_duckdb_conn


def update_seller_deal_table(new_deals: list[Book]):
    """Adds new deals to the database and marks old deals as deleted

    :param new_deals:
    """

    # This could be done using a temp table for the new deals, but that feels like overkill
    # I can't imagine there's ever going to be more than 5,000 books in someone's TBR
    # If it were any larger we'd have bigger problems.
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
        print(f"{str(deal)} is no longer active")
        deal.deleted = True
        df_data.append(deal.dict())

    if df_data:
        df = pd.DataFrame(df_data)

        db_conn = get_duckdb_conn()
        db_conn.register("_df", df)
        db_conn.execute("INSERT INTO seller_deal SELECT * FROM _df;")
        db_conn.unregister("_df")


def _retry_books(found_books: list[Book], all_books: list[dict]) -> list[dict]:
    response = []
    found_book_set = {f'{b.title} - {b.authors}' for b in found_books}
    for book in all_books:
        if ":" not in book["Title"]:
            continue

        if f'{book["Title"]} - {book["Authors"]}' not in found_book_set:
            book["Title"] = book["Title"].split(":")[0]
            response.append(book)

    return response


async def _get_books(config, seller: Seller, books: list[dict]) -> list[Book]:
    """Get Books with limited concurrency."""
    semaphore = asyncio.Semaphore(10)
    response = []
    unresolved_books = []

    tasks = [
        seller.get_book(book["Title"], book["Authors"], config.run_time, semaphore)
        for book in books
        if book["Read Status"] == "to-read"
    ]
    results = await tqdm_asyncio.gather(*tasks, desc=f"Getting latest prices from {seller.name}")
    for book in results:
        if book.exists and book.current_price <= config.max_price and book.discount() >= config.min_discount:
            response.append(book)
        elif not book.exists:
            unresolved_books.append(book)

    if retry_books := _retry_books(response, books):
        print("Attempting to find missing books with alternate title")
        response.extend(await _get_books(config, seller, retry_books))
    elif unresolved_books:
        print()
        for book in unresolved_books:
            print(f"{book.title} by {book.authors} not found")

    return response


async def get_latest_deals(config: Config):
    books: list[Book] = []
    checked_deals: set[str] = set()

    def _get_deal_base(title: str, authors: str) -> str:
        return f'{title}__{authors}'

    for story_graph_export_path in config.story_graph_export_paths:
        print(f"Deals for {story_graph_export_path}")

        with open(story_graph_export_path, 'r', newline='', encoding='utf-8') as file:
            # Use csv.DictReader to get dictionaries with column headers
            tbr_books: list[dict] = [
                book for book in csv.DictReader(file)
                if _get_deal_base(book["Title"], book["Authors"]) not in checked_deals
            ]  # type: ignore

        for seller in [Audible(), Chirp()]:
            await seller.set_auth()

            print("---------------\n")
            print(f"Getting deals from {seller.name}")
            print("\n---------------")
            books.extend(await _get_books(config, seller, tbr_books[:10]))

        checked_deals.update(
            {_get_deal_base(b.title, b.authors) for b in books}
        )
        print("---------------\n")

    update_seller_deal_table(books)
