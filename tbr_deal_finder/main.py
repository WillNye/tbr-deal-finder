import asyncio
import os
from datetime import timedelta
from textwrap import dedent
from typing import Union

import click
import questionary

from tbr_deal_finder.config import Config
from tbr_deal_finder.library_exports import maybe_set_library_export_audiobook_isbn
from tbr_deal_finder.migrations import make_migrations
from tbr_deal_finder.book import get_deals_found_at, print_books, get_active_deals
from tbr_deal_finder.retailer import RETAILER_MAP
from tbr_deal_finder.retailer_deal import get_latest_deals
from tbr_deal_finder.utils import get_duckdb_conn, get_query_by_name, execute_query


@click.group()
def cli():
    make_migrations()

    # Check that the config exists for all commands ran
    try:
        Config.load()
    except FileNotFoundError:
        _set_config()


def _add_path(existing_paths: list[str]) -> Union[str, None]:
    try:
        new_path = os.path.expanduser(click.prompt("What is the new path"))
        if new_path in existing_paths:
            click.echo(f"{new_path} is already being tracked.\n")
            return None
        elif os.path.exists(new_path):
            return new_path
        else:
            click.echo(f"Could not find {new_path}. Please try again.\n")
            return _add_path(existing_paths)
    except (KeyError, KeyboardInterrupt, TypeError):
        return None


def _remove_path(existing_paths: list[str]) -> Union[str, None]:
    try:
        return questionary.select(
            "Which path would you like to remove?",
            choices=existing_paths,
        ).ask()
    except (KeyError, KeyboardInterrupt, TypeError):
        return None


def _set_library_export_paths(config: Config):
    """
    Interactively set the paths to the user's library export files.

    Allows the user to add or remove paths to their StoryGraph, Goodreads, or custom CSV export files.
    Ensures that only valid, unique paths are added. Updates the config in-place.
    """
    while True:
        if config.library_export_paths:
            if len(config.library_export_paths) > 1:
                choices = ["Add new path", "Remove path", "Done"]
            else:
                choices = ["Add new path", "Done"]

            try:
                user_selection = questionary.select(
                    "What change would you like to make to your library export paths",
                    choices=choices,
                ).ask()
            except (KeyError, KeyboardInterrupt, TypeError):
                return
        else:
            click.echo("Add your library export path.")
            user_selection = "Add new path"

        if user_selection == "Done":
            return
        elif user_selection == "Add new path":
            if new_path := _add_path(config.library_export_paths):
                config.library_export_paths.append(new_path)
        else:
            if remove_path := _remove_path(config.library_export_paths):
                config.library_export_paths.remove(remove_path)


def _set_locale(config: Config):
    locale_options = {
        "US and all other countries not listed": "us",
        "Canada": "ca",
        "UK and Ireland": "uk",
        "Australia and New Zealand": "au",
        "France, Belgium, Switzerland": "fr",
        "Germany, Austria, Switzerland": "de",
        "Japan": "jp",
        "Italy": "it",
        "India": "in",
        "Spain": "es",
        "Brazil": "br"
    }
    default_locale = [k for k,v in locale_options.items() if v == config.locale][0]

    try:
        user_selection = questionary.select(
            "What change would you like to make to your library export paths",
            choices=list(locale_options.keys()),
            default=default_locale
        ).ask()
    except (KeyError, KeyboardInterrupt, TypeError):
        return

    config.set_locale(locale_options[user_selection])


def _set_tracked_retailers(config: Config):
    config.set_tracked_retailers(
        questionary.checkbox(
            "Select the retailers you want to check deals for. "
            "Tip: Chirp doesn't have a subscription and can have good deals. I'd recommend checking it.",
            choices=[
                questionary.Choice(retailer, checked=retailer in config.tracked_retailers)
                for retailer in RETAILER_MAP.keys()
            ]).ask()
    )


def _set_config() -> Config:
    try:
        config = Config.load()
    except FileNotFoundError:
        config = Config(library_export_paths=[], tracked_retailers=list(RETAILER_MAP.keys()))

    # Setting these config values are a little more involved,
    #   so they're broken out into their own functions
    _set_library_export_paths(config)
    _set_tracked_retailers(config)
    _set_locale(config)

    config.max_price = click.prompt(
        "Enter maximum price for deals",
        type=float,
        default=config.max_price
    )
    config.min_discount = click.prompt(
        "Enter minimum discount percentage",
        type=int,
        default=config.min_discount
    )

    config.save()
    click.echo("Configuration saved!")

    return config


@cli.command()
def setup():
    _set_config()


@cli.command()
def latest_deals():
    """Find book deals from your Library export."""
    config = Config.load()

    asyncio.run(maybe_set_library_export_audiobook_isbn(config))

    db_conn = get_duckdb_conn()
    results = execute_query(
        db_conn,
        get_query_by_name("get_active_deals.sql")
    )
    last_ran = None if not results else results[0]["timepoint"]
    min_age = config.run_time - timedelta(hours=8)

    if not last_ran or last_ran < min_age:
        try:
            asyncio.run(get_latest_deals(config))
        except Exception as e:
            ran_successfully = False
            details = f"Error getting deals: {e}"
            click.echo(details)
        else:
            ran_successfully = True
            details = ""

        # Save execution results
        db_conn.execute(
            "INSERT INTO latest_deal_run_history (timepoint, ran_successfully, details) VALUES (?, ?, ?)",
            [config.run_time, ran_successfully, details]
        )

        if not ran_successfully:
            # Gracefully exit on Exception raised by get_latest_deals
            return

    else:
        click.echo(dedent("""
        To prevent abuse lastest deals can only be pulled every 8 hours.
        Fetching most recent deal results.\n
        """))
        config.run_time = last_ran

    if books := get_deals_found_at(config.run_time):
        print_books(books)
    else:
        click.echo("No new deals found.")


@cli.command()
def active_deals():
    """Get all active deals."""
    if books := get_active_deals():
        print_books(books)
    else:
        click.echo("No deals found.")


if __name__ == '__main__':
    cli()
