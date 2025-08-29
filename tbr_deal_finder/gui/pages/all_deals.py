import logging

import flet as ft

from tbr_deal_finder.book import get_active_deals, Book, is_qualifying_deal
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage

logger = logging.getLogger(__name__)

class AllDealsPage(BaseBookPage):
    def __init__(self, app):
        super().__init__(app, items_per_page=6)
        
    def get_page_title(self) -> str:
        return "All Active Deals"
    
    def get_empty_state_message(self) -> tuple[str, str]:
        return ("No deals found", "Try adjusting your search or filters")
    
    def load_items(self):
        """Load active deals from database"""
        try:
            self.items = [
                book for book in get_active_deals()
                if is_qualifying_deal(self.app.config, book)
            ]
            self.apply_filters()
        except Exception as e:
            self.items = []
            self.filtered_items = []
            logger.error(f"Error loading deals: {e}")

    def create_item_tile(self, deal: Book):
        """Create a tile for a single deal"""
        # Truncate title if too long
        title = deal.title
        if len(title) > 60:
            title = f"{title[:60]}..."
        
        # Format price and discount
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