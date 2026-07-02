import flet as ft

from tbr_deal_finder.book import Book
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage
from tbr_deal_finder.gui.widgets import book_tile_card, cover_image_for_format, truncate_title


class BaseDealsPage(BaseBookPage):
    """Shared base for pages that list deals, unifying tile formatting."""

    def create_item_tile(self, deal: Book) -> ft.Control:  # type: ignore[override]
        price_text = f"{deal.current_price_string()} ({deal.discount()}% off)"
        original_price = deal.list_price_string()

        return book_tile_card(
            cover_image_for_format(deal.image_url, deal.format),
            [
                ft.Text(deal.retailer, weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.BLUE_400),
                ft.Text(truncate_title(deal.title), weight=ft.FontWeight.BOLD),
                ft.Text(f"by {deal.authors}", color=ft.Colors.GREY_600),
                ft.Row([
                    ft.Text(price_text, color=ft.Colors.GREEN, weight=ft.FontWeight.BOLD),
                    ft.Text(f"was {original_price}", color=ft.Colors.GREY_500, size=12),
                ], wrap=True, spacing=8),
            ],
            overlay=ft.IconButton(
                icon=ft.Icons.VISIBILITY,
                tooltip="Toggle price tracking",
                on_click=lambda e, book=deal: self.show_price_tracking_dialog(book),
                icon_size=20
            ),
            on_click=lambda e, book=deal: self.app.show_book_details(book, book.format),
        )


