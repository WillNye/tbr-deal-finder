import logging

import flet as ft

from tbr_deal_finder.book import Book
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage
from tbr_deal_finder.owned_books import get_owned_books

logger = logging.getLogger(__name__)

class OwnedBooksPage(BaseBookPage):
    def __init__(self, app):
        super().__init__(app, items_per_page=6)
        
    def get_page_title(self) -> str:
        return "My Owned Books"
    
    def get_empty_state_message(self) -> tuple[str, str]:
        return (
            "No owned books found",
            "Make sure you have books in your library and your retailers are configured"
        )
    
    def load_items(self):
        """Load owned books from configured retailers"""
        if not self.app.config:
            self.items = []
            self.filtered_items = []
            return
        
        # Set loading state and use Flet's proper async task runner
        self.set_loading(True)
        self.app.page.run_task(self._async_load_items)

    async def _async_load_items(self):
        """Load owned books asynchronously using Flet's async support"""
        # Disable navigation during the loading operation
        self.app.disable_navigation()
        
        try:
            # Run the async operation directly
            await self.app.auth_all_configured_retailers()
            self.items = await get_owned_books(self.app.config)
            self.apply_filters()
        except Exception as e:
            logger.error(f"Error loading owned books: {e}")
            self.items = []
            self.filtered_items = []
        finally:
            self.set_loading(False)
            
            # Re-enable navigation after the operation completes
            self.app.enable_navigation()
            
            # Update the page to reflect the loaded data
            self.app.page.update()

    def create_item_tile(self, book: Book):
        """Create a non-clickable tile for an owned book"""
        # Truncate title if too long
        title = book.title
        if len(title) > 60:
            title = f"{title[:60]}..."
        
        # Format retailer and format info
        format_text = book.format.value if book.format else "Unknown"
        
        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    title=ft.Text(title, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Column([
                        ft.Text(f"by {book.authors}", color=ft.Colors.GREY_600),
                        ft.Row([
                            ft.Text(f"Format: {format_text}", color=ft.Colors.BLUE_600, size=12),
                            ft.Text(f"From: {book.retailer}", color=ft.Colors.GREY_500, size=12)
                        ])
                    ], spacing=2),
                    trailing=ft.Column([
                        ft.Icon(ft.Icons.LIBRARY_BOOKS, color=ft.Colors.GREEN_600, size=20)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    # No on_click handler - tiles are not clickable
                ),
                padding=10,
                # No on_click handler - container is not clickable
            )
        )
