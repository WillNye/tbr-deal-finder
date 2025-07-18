import asyncio

import click

from tbr_deal_finder.config import Config
from tbr_deal_finder.migrations import make_migrations
from tbr_deal_finder.book import get_deals_found_at, print_books
from tbr_deal_finder.seller_deal import get_latest_deals


@click.command()
def main():
    """Find book deals from your StoryGraph export."""
    make_migrations()

    try:
        config = Config.load()
    except FileNotFoundError:
        click.echo("Configuration file not found. Let's set it up!")
        
        # Prompt for config values
        story_graph_export_paths = click.prompt("Enter the paths to your StoryGraph export CSV file as a comma-separated list")
        
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
        click.echo("Select your locale:")
        for idx, (desc, code) in enumerate(locale_options, 1):
            click.echo(f"  {idx}. {desc} [{code}]")
        locale_choice = click.prompt(
            "Enter the number corresponding to your locale",
            type=click.IntRange(1, len(locale_options)),
            default=1
        )
        locale = locale_options[locale_choice - 1][1]
        
        max_price = click.prompt(
            "Enter maximum price for deals",
            type=float,
            default=8.0
        )
        min_discount = click.prompt(
            "Enter minimum discount percentage",
            type=int,
            default=35
        )
        
        config = Config(
            story_graph_export_paths=story_graph_export_paths,
            locale=locale,
            max_price=max_price,
            min_discount=min_discount
        )
        config.save()
        click.echo("Configuration saved!")

    # TODO: Re-enable _set_isbn when set_book_audio_isbn is working
    # _set_isbn(config)
    asyncio.run(get_latest_deals(config))

    if books := get_deals_found_at(config.run_time):
        print_books(books)


if __name__ == '__main__':
    main()
