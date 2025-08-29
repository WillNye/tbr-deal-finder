import logging

import flet as ft
import asyncio
import threading

from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.tracked_books import get_tbr_books
from .base_book_page import BaseBookPage

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
        
        # Set loading state and run async operation in a thread
        self.set_loading(True)
        thread = threading.Thread(target=self._run_async_load)
        thread.daemon = False  # Don't block app shutdown
        thread.start()

    def _run_async_load(self):
        """Run the async load operation in a new event loop"""
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async operation
            loop.run_until_complete(self._async_load_items())
        finally:
            # Properly cleanup any pending tasks
            self._cleanup_event_loop(loop)
    
    def _cleanup_event_loop(self, loop):
        """Properly cleanup the event loop and any pending tasks"""
        try:
            # Give any pending tasks a moment to complete
            pending = asyncio.all_tasks(loop)
            if pending:
                # Cancel all pending tasks
                for task in pending:
                    task.cancel()
                
                # Wait for cancelled tasks to finish
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            logger.error(f"Error during event loop cleanup: {e}")
        finally:
            loop.close()
    
    async def _async_load_items(self):
        """Async method to load TBR books"""
        try:
            self.items = await get_tbr_books(self.app.config)
            self.apply_filters()
        except Exception as e:
            self.items = []
            self.filtered_items = []
            logger.error(f"Error loading books: {e}")
        finally:
            self.set_loading(False)

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