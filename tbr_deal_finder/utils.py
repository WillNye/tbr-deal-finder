import re
from typing import Optional

import click
import duckdb

from tbr_deal_finder import TBR_DEALS_PATH, QUERY_PATH


def currency_to_float(price_str):
    """Parse various price formats to float."""
    if not price_str:
        return 0.0

    # Remove currency symbols, commas, and whitespace
    cleaned = re.sub(r'[^\d.]', '', str(price_str))

    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def get_duckdb_conn():
    return duckdb.connect(TBR_DEALS_PATH.joinpath("tbr_deal_finder.db"))


def execute_query(
    db_conn: duckdb.DuckDBPyConnection,
    query: str,
    query_params: Optional[dict] = None,
) -> list[dict]:
    q = db_conn.execute(query, query_params if query_params is not None else {})
    rows = q.fetchall()
    assert q.description
    column_names = [desc[0] for desc in q.description]
    return [dict(zip(column_names, row)) for row in rows]


def get_query_by_name(file_name: str) -> str:
    return QUERY_PATH.joinpath(file_name).read_text()


def echo_err(message):
    click.secho(f'\n❌  {message}\n', fg='red', bold=True)


def echo_success(message):
    click.secho(f'\n✅  {message}', fg='green', bold=True)


def echo_warning(message):
    click.secho(f'\n⚠️  {message}', fg='yellow')


def echo_info(message):
    click.secho(f'{message}', fg='blue')
