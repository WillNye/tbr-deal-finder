import asyncio
import os
from typing import Union

import click
import questionary

from tbr_deal_finder.config import Config
from tbr_deal_finder.migrations import make_migrations
from tbr_deal_finder.book import get_deals_found_at, print_books, get_active_deals
from tbr_deal_finder.seller_deal import get_latest_deals


@click.group()
def cli():
    make_migrations()


def _add_path(existing_paths: list[str]) -> Union[str, None]:
    try:
        new_path = os.path.expanduser(click.prompt("What is the new path"))
        if new_path in existing_paths:
            print(f"{new_path} is already being tracked.\n")
            return None
        elif os.path.exists(new_path):
            return new_path
        else:
            print(f"Could not find {new_path}. Please try again.\n")
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


def _set_storygraph_paths(config: Config):
    while True:
        if config.story_graph_export_paths:
            if len(config.story_graph_export_paths) > 1:
                choices = ["Add new path", "Remove path", "Done"]
            else:
                choices = ["Add new path", "Done"]

            try:
                user_selection = questionary.select(
                    "What change would you like to make to your StoryGraph export paths",
                    choices=choices,
                ).ask()
            except (KeyError, KeyboardInterrupt, TypeError):
                return
        else:
            print("Add your StoryGraph export path.")
            user_selection = "Add new path"

        if user_selection == "Done":
            return
        elif user_selection == "Add new path":
            if new_path := _add_path(config.story_graph_export_paths):
                config.story_graph_export_paths.append(new_path)
        else:
            if remove_path := _remove_path(config.story_graph_export_paths):
                config.story_graph_export_paths.remove(remove_path)


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
            "What change would you like to make to your StoryGraph export paths",
            choices=list(locale_options.keys()),
            default=default_locale
        ).ask()
    except (KeyError, KeyboardInterrupt, TypeError):
        return

    config.set_locale(locale_options[user_selection])


def _set_config() -> Config:
    try:
        config = Config.load()
    except FileNotFoundError:
        config = Config(story_graph_export_paths=[])

    # Prompt for config values
    _set_storygraph_paths(config)

    # Locale selection
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
    """Find book deals from your StoryGraph export."""
    try:
        config = Config.load()
    except FileNotFoundError:
        config = _set_config()

    # TODO: Re-enable _set_isbn when set_book_audio_isbn is working
    # _set_isbn(config)
    asyncio.run(get_latest_deals(config))

    if books := get_deals_found_at(config.run_time):
        print_books(books)
    else:
        print("No new deals found.")


@cli.command()
def active_deals():
    """Find book deals from your StoryGraph export."""
    if books := get_active_deals():
        print_books(books)
    else:
        print("No deals found.")


if __name__ == '__main__':
    cli()
