import asyncio

import click

from tbr_deal_finder.config import Config
from tbr_deal_finder.migrations import make_migrations
from tbr_deal_finder.book import get_deals_found_at, print_books, get_active_deals
from tbr_deal_finder.seller_deal import get_latest_deals


@click.group()
def cli():
    make_migrations()


def _set_config() -> Config:
    try:
        config = Config.load()
    except FileNotFoundError:
        config = Config(story_graph_export_paths=[])

    # Prompt for config values
    story_graph_export_paths = click.prompt(
        "Enter the paths to your StoryGraph export CSV file as a comma-separated list",
        default=config.story_graph_export_paths_str,
    )
    config.set_story_graph_export_paths(story_graph_export_paths)

    # Locale selection
    locale_options = [
        ("US and all other countries not listed", "us"),
        ("Canada", "ca"),
        ("UK and Ireland", "uk"),
        ("Australia and New Zealand", "au"),
        ("France, Belgium, Switzerland", "fr"),
        ("Germany, Austria, Switzerland", "de"),
        ("Japan", "jp"),
        ("Italy", "it"),
        ("India", "in"),
        ("Spain", "es"),
        ("Brazil", "br"),
    ]
    default_locale = next(i for i, (_, code) in enumerate(locale_options, 1) if code == config.locale)

    click.echo("Select your locale:")
    for idx, (desc, code) in enumerate(locale_options, 1):
        click.echo(f"  {idx}. {desc} [{code}]")
    locale_choice = click.prompt(
        "Enter the number corresponding to your locale",
        type=click.IntRange(1, len(locale_options)),
        default=default_locale
    )
    config.set_locale(locale_options[locale_choice - 1][1])

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


@cli.command()
def active_deals():
    """Find book deals from your StoryGraph export."""
    if books := get_active_deals():
        print_books(books)


if __name__ == '__main__':
    cli()
