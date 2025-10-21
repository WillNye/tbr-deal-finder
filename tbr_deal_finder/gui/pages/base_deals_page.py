import flet as ft

from tbr_deal_finder.book import Book
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage


class BaseDealsPage(BaseBookPage):
    """Shared base for pages that list deals, unifying tile formatting."""

    def create_item_tile(self, deal: Book) -> ft.Control:  # type: ignore[override]
        # Truncate title if too long to keep tiles compact
        title = deal.title
        if len(title) > 60:
            title = f"{title[:60]}..."

        # Format price, discount, and original price text
        price_text = f"{deal.current_price_string()} ({deal.discount()}% off)"
        original_price = deal.list_price_string()

        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    title=ft.Text(title, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Column([
                        ft.Text(f"by {deal.authors}", color=ft.Colors.GREY_600),
                        ft.Row([
                            ft.Text(price_text, color=ft.Colors.GREEN, weight=ft.FontWeight.BOLD),
                            ft.Text(f"was {original_price}", color=ft.Colors.GREY_500, size=12)
                        ])
                    ], spacing=2),
                    trailing=ft.Column([
                        ft.Text(deal.retailer, weight=ft.FontWeight.BOLD, size=12)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    on_click=lambda e, book=deal: self.app.show_book_details(book, book.format)
                ),
                padding=10,
                on_click=lambda e, book=deal: self.app.show_book_details(book, book.format)
            )
        )


