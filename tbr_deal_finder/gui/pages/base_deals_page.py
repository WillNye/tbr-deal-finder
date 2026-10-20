from typing import List, Optional

import flet as ft

from tbr_deal_finder.book import Book
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage
from tbr_deal_finder.gui.widgets import book_tile_card, cover_image_for_format, truncate_title


NO_CUSTOM_DEAL_FILTER = "None"
EXCLUDE_CUSTOM_DEALS = "Exclude Custom Deals"


class BaseDealsPage(BaseBookPage):
    """Shared base for pages that list deals, unifying tile formatting."""

    def __init__(self, app, rows_per_page: int = 3):
        super().__init__(app, rows_per_page)
        self.custom_deal_filter = NO_CUSTOM_DEAL_FILTER
        # Custom deal types among the deals matching every other filter.
        self.custom_deal_types: List[str] = []

    def get_extra_filter_controls(self) -> List[ft.Control]:
        self.custom_deal_dropdown = ft.Dropdown(
            label="Custom Deal",
            value=self.custom_deal_filter,
            options=self._custom_deal_filter_options(),
            on_change=self.on_custom_deal_change,
            width=200,
        )
        return [self.custom_deal_dropdown]

    def _custom_deal_filter_options(self) -> List[ft.dropdown.Option]:
        return [
            ft.dropdown.Option(option)
            for option in [NO_CUSTOM_DEAL_FILTER, EXCLUDE_CUSTOM_DEALS, *self.custom_deal_types]
        ]

    def apply_extra_filters(self, items: List[Book]) -> List[Book]:
        deal_types = {item.custom_deal_type for item in items if item.custom_deal_type}
        if self.custom_deal_filter not in (NO_CUSTOM_DEAL_FILTER, EXCLUDE_CUSTOM_DEALS):
            # Keep the active selection listed even when other filters leave it with no matches.
            deal_types.add(self.custom_deal_filter)
        self.custom_deal_types = sorted(deal_types)
        if hasattr(self, "custom_deal_dropdown"):
            self.custom_deal_dropdown.options = self._custom_deal_filter_options()

        if self.custom_deal_filter == NO_CUSTOM_DEAL_FILTER:
            return items
        if self.custom_deal_filter == EXCLUDE_CUSTOM_DEALS:
            return [item for item in items if not item.custom_deal_type]
        return [item for item in items if item.custom_deal_type == self.custom_deal_filter]

    def on_custom_deal_change(self, e):
        self.custom_deal_filter = e.control.value
        self.apply_filters()
        self.update_items_display()

    def reset_custom_deal_filter(self):
        self.custom_deal_filter = NO_CUSTOM_DEAL_FILTER
        if hasattr(self, "custom_deal_dropdown"):
            self.custom_deal_dropdown.value = NO_CUSTOM_DEAL_FILTER

    def refresh_page_state(self):
        self.reset_custom_deal_filter()
        super().refresh_page_state()

    @staticmethod
    def custom_deal_label(deal: Book) -> Optional[ft.Control]:
        """Badge naming the deal's custom deal type, with its details on hover."""
        if not deal.custom_deal_type:
            return None
        return ft.Row(
            [
                ft.Icon(ft.Icons.LOCAL_OFFER, size=14, color=ft.Colors.AMBER),
                ft.Text(
                    deal.custom_deal_type,
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.AMBER,
                    tooltip=deal.custom_deal_details,
                ),
            ],
            spacing=4,
            tight=True,
        )

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

        info = [
            ft.Text(deal.retailer, weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.BLUE_400),
            ft.Text(truncate_title(deal.title), weight=ft.FontWeight.BOLD),
            ft.Text(f"by {deal.authors}", color=ft.Colors.GREY_600),
            ft.Row([
                ft.Text(price_text, color=ft.Colors.GREEN, weight=ft.FontWeight.BOLD),
                ft.Text(f"was {original_price}", color=ft.Colors.GREY_500, size=12),
            ], wrap=True, spacing=8),
        ]
        if custom_deal := self.custom_deal_label(deal):
            info.append(custom_deal)

        return book_tile_card(
            cover_image_for_format(deal.image_url, deal.format),
            info,
            overlay=self._deal_actions_overlay(deal),
            on_click=lambda e, book=deal: self.app.show_book_details(book, book.format),
        )


