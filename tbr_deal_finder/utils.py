import datetime
import functools
import os
import re
import sys
from pathlib import Path
from typing import Optional

import click
import duckdb

from tbr_deal_finder import QUERY_PATH


@functools.cache
def is_gui_env() -> bool:
    return os.environ.get("ENTRYPOINT", "GUI") == "GUI"


@functools.cache
def get_data_dir() -> Path:
    """
    Get the appropriate user data directory for each platform
    following OS conventions
    """
    app_author = "WillNye"
    app_name = "TBR Deal Finder"

    if custom_path := os.getenv("TBR_DEAL_FINDER_CUSTOM_PATH"):
        path = Path(custom_path).expanduser()
    else:
        cli_path = Path.home() / ".tbr_deal_finder"
        if sys.platform == "win32":
            # Windows: C:\Users\Username\AppData\Local\AppAuthor\AppName
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            gui_path = Path(base) / app_author / app_name

        elif sys.platform == "darwin":
            # macOS: ~/Library/Application Support/AppName
            gui_path = Path.home() / "Library" / "Application Support" / app_name

        else:  # Linux and others
            # Linux: ~/.local/share/appname (following XDG spec)
            xdg_data_home = os.environ.get("XDG_DATA_HOME",
                                           os.path.expanduser("~/.local/share"))
            gui_path = Path(xdg_data_home) / app_name.lower()

        if is_gui_env():
            path = gui_path
            if cli_path.exists() and not path.exists():
                # Use the cli path if it exists and the gui path does not
                path = cli_path
        else:
            path = cli_path
            if gui_path.exists() and not path.exists():
                # Use the gui path if it exists and the cli path does not
                path = gui_path

    # Create directory if it doesn't exist
    path.mkdir(parents=True, exist_ok=True)
    return path

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


def float_to_currency(val: float) -> str:
    from tbr_deal_finder.config import Config
    return f"{Config.currency_symbol()}{val:.2f}"


def get_duckdb_conn():
    return duckdb.connect(get_data_dir().joinpath("tbr_deal_finder.db"))


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


def get_latest_deal_last_ran(
    db_conn: duckdb.DuckDBPyConnection
) -> Optional[datetime.datetime]:

    results = execute_query(
        db_conn,
        QUERY_PATH.joinpath("latest_deal_last_ran_most_recent_success.sql").read_text(),
    )
    if not results:
        return None
    return results[0]["timepoint"]


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
