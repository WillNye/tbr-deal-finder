import logging

import flet as ft

from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.tracked_books import get_tbr_books
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage

logger = logging.getLogger(__name__)


class AllBooksPage(BaseBookPage):
    def __init__(self, app):
        super().__init__(app, items_per_page=7)
        
    def get_page_title(self) -> str:
        return "My Books"
    
    def get_empty_state_message(self) -> tuple[str, str]:
        return (
            "No books found", 
            "Try adjusting your search or check your library export files in settings"
        )
    
    def get_format_filter_options(self):
        """Include 'Either Format' option for TBR books"""
        return ["All", "E-Book", "Audiobook", "Either Format"]
    
    def load_items(self):
        """Load TBR books from database"""
        if not self.app.config:
            self.items = []
            self.filtered_items = []
            return
        
        # Set loading state and use Flet's proper async task runner
        self.set_loading(True)
        self.app.page.run_task(self._async_load_items)

    async def _async_load_items(self):
        """Load TBR books asynchronously using Flet's async support"""
        # Disable navigation during the loading operation
        self.app.disable_navigation()
        
        try:
            # Run the async operation directly
            await self.app.auth_all_configured_retailers()
            self.items = await get_tbr_books(self.app.config)
            self.apply_filters()
        except Exception as e:
            logger.error(f"Error loading TBR books: {e}")
            self.items = []
            self.filtered_items = []
        finally:
            self.set_loading(False)
            
            # Re-enable navigation after the operation completes
            self.app.enable_navigation()
            
            # Update the page to reflect the loaded data
            self.app.page.update()


    def filter_by_format(self, items, format_filter: str):
        """Custom format filter that includes 'Either Format' option"""
        if format_filter == "E-Book":
            return [item for item in items if item.format == BookFormat.EBOOK]
        elif format_filter == "Audiobook":
            return [item for item in items if item.format == BookFormat.AUDIOBOOK]
        elif format_filter == "Either Format":
            return [item for item in items if item.format == BookFormat.NA]
        else:
            return items

    def create_item_tile(self, book: Book):
        """Create a tile for a single book"""
        # Truncate title if too long
        title = book.title
        if len(title) > 60:
            title = f"{title[:60]}..."

        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    title=ft.Text(title, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Column([
                        ft.Text(f"by {book.authors}", color=ft.Colors.GREY_600),
                    ], spacing=2),
                    on_click=lambda e, b=book: self.app.show_book_details(b, b.format)
                ),
                padding=10,
                on_click=lambda e, b=book: self.app.show_book_details(b, b.format)
            )
        )

    def check_book_has_deals(self, book: Book) -> bool:
        """Check if a book has active deals (simplified check)"""
        # This is a simplified check - in a real implementation you might
        # want to query the deals database to see if this book has active deals
        return False  # Placeholder