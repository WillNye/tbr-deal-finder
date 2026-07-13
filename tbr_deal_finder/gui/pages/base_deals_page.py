import flet as ft

from tbr_deal_finder.book import Book
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage
from tbr_deal_finder.gui.widgets import book_tile_card, cover_image_for_format, truncate_title


class BaseDealsPage(BaseBookPage):
    """Shared base for pages that list deals, unifying tile formatting."""

    def _deal_actions_overlay(self, deal: Book) -> ft.Row:
        """Top-right action icons shared by all deal tiles: copy title, view
        deal (only when a product URL exists), and the price-tracking toggle."""
        buttons = [
            ft.IconButton(
                icon=ft.Icons.COPY,
                tooltip="Copy title",
                icon_size=20,
                on_click=lambda e, b=deal: self._copy_title(b),
            ),
        ]
        if deal.product_url:
            buttons.append(
                ft.IconButton(
                    icon=ft.Icons.OPEN_IN_NEW,
                    tooltip=f"View on {deal.retailer}",
                    icon_size=20,
                    on_click=lambda e, u=deal.product_url: self.app.page.launch_url(u),
                )
            )
        buttons.append(
            ft.IconButton(
                icon=ft.Icons.VISIBILITY,
                tooltip="Toggle price tracking",
                icon_size=20,
                on_click=lambda e, b=deal: self.show_price_tracking_dialog(b),
            )
        )
        return ft.Row(buttons, spacing=0, tight=True)

    def _copy_title(self, deal: Book) -> None:
        """Copy the deal's title to the clipboard and confirm with a snackbar."""
        self.app.page.set_clipboard(deal.title)
        self._show_snack("Copied title")

    def _show_snack(self, message: str) -> None:
        self.app.page.open(ft.SnackBar(ft.Text(message)))

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
            overlay=self._deal_actions_overlay(deal),
            on_click=lambda e, book=deal: self.app.show_book_details(book, book.format),
        )


