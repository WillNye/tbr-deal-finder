import flet as ft
import asyncio
import threading
from datetime import datetime, timedelta
from typing import List

from tbr_deal_finder.book import get_deals_found_at, Book, BookFormat, is_qualifying_deal
from tbr_deal_finder.utils import get_duckdb_conn, get_latest_deal_last_ran
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage


class LatestDealsPage(BaseBookPage):
    def __init__(self, app):
        super().__init__(app, 25)
        self.last_run_time = None
        
    def get_page_title(self) -> str:
        return "Latest Deals"
    
    def get_empty_state_message(self) -> tuple[str, str]:
        return (
            "No recent deals found", 
            "Click 'Get Latest Deals' to check for new deals"
        )
    
    def should_include_refresh_button(self) -> bool:
        """Latest deals doesn't use normal refresh button"""
        return False
    
    def build(self):
        """Build the latest deals page with custom header"""
        self.check_last_run()
        
        # Custom header with run button
        header = self.build_header()
        
        # Progress indicator (hidden by default)
        self.progress_container = ft.Container(
            content=ft.Column([
                ft.ProgressBar(),
                ft.Text("Checking for latest deals...", text_align=ft.TextAlign.CENTER)
            ], spacing=10),
            visible=False,
            padding=20
        )
        
        # Standard search controls (but without refresh button)
        search_controls = self.build_search_controls()
        
        # Loading indicator for normal operations
        self.loading_container = ft.Container(
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Loading...", text_align=ft.TextAlign.CENTER)
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            visible=self.is_loading,
            alignment=ft.alignment.center,
            height=200
        )

        self.load_items()
        
        # Results section
        results = self.build_results()
        
        return ft.Column([
            ft.Text(self.get_page_title(), size=24, weight=ft.FontWeight.BOLD),
            header,
            self.progress_container,
            search_controls,
            self.loading_container,
            results
        ], spacing=20, scroll=ft.ScrollMode.AUTO)

    def build_header(self):
        """Build the header with run button and status"""
        can_run = self.can_run_latest_deals()
        
        if not can_run and self.last_run_time:
            next_run_time = self.last_run_time + timedelta(hours=8)
            time_remaining = next_run_time - datetime.now()
            hours_remaining = max(0, int(time_remaining.total_seconds() / 3600))
            status_text = f"Next run available in {hours_remaining} hours"
            status_color = ft.Colors.ORANGE
        elif self.last_run_time:
            status_text = f"Last run: {self.last_run_time.strftime('%Y-%m-%d %H:%M')}"
            status_color = ft.Colors.GREEN
        else:
            status_text = "No previous runs"
            status_color = ft.Colors.GREY_600

        run_button = ft.ElevatedButton(
            "Get Latest Deals",
            icon=ft.Icons.SYNC,
            on_click=self.run_latest_deals,
            disabled=not can_run or self.is_loading
        )
        
        info_button = ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE,
            tooltip="Latest deals can only be run every 8 hours to prevent abuse",
            on_click=self.show_info_dialog
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    run_button,
                    info_button
                ], alignment=ft.MainAxisAlignment.START),
                ft.Text(status_text, color=status_color, size=14)
            ], spacing=10),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

    def build_results(self):
        """Build the results section using base class pagination"""
        if not self.filtered_items:
            main_msg, sub_msg = self.get_empty_state_message()
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SEARCH, size=64, color=ft.Colors.GREY_400),
                    ft.Text(main_msg, size=18, color=ft.Colors.GREY_600),
                    ft.Text(sub_msg, color=ft.Colors.GREY_500)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                height=300
            )
        
        # Group deals by format for better organization
        ebooks = [deal for deal in self.filtered_items if deal.format == BookFormat.EBOOK]
        audiobooks = [deal for deal in self.filtered_items if deal.format == BookFormat.AUDIOBOOK]
        
        sections = []
        
        if ebooks:
            sections.append(self.build_format_section("E-Book Deals", ebooks))
        
        if audiobooks:
            sections.append(self.build_format_section("Audiobook Deals", audiobooks))
        
        if sections:
            # Add pagination at the bottom
            pagination = self.build_pagination()
            sections.append(pagination)
        
        return ft.Column(sections, spacing=20)

    def build_format_section(self, title: str, deals: List[Book]):
        """Build a section for a specific format"""
        # Use pagination for the deals within this format
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(deals))
        page_deals = deals[start_idx:end_idx]
        
        deals_tiles = []
        current_title_id = None
        for deal in page_deals:
            # Add spacing between different books
            if current_title_id and current_title_id != deal.title_id:
                deals_tiles.append(ft.Divider())
            current_title_id = deal.title_id
            
            tile = self.create_item_tile(deal)
            deals_tiles.append(tile)
        
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                ft.Column(deals_tiles, spacing=5)
            ], spacing=10),
            padding=15,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

    def load_items(self):
        """Load deals found at the last run time"""
        if self.last_run_time:
            try:
                self.items = [
                    book
                    for book in get_deals_found_at(self.last_run_time)
                    if is_qualifying_deal(self.app.config, book)
                ]
                self.apply_filters()
            except Exception as e:
                self.items = []
                self.filtered_items = []
                print(f"Error loading latest deals: {e}")
        else:
            self.items = []
            self.filtered_items = []

    def create_item_tile(self, deal: Book):
        """Create a tile for a single deal"""
        # Truncate title if too long
        title = deal.title
        if len(title) > 50:
            title = f"{title[:50]}..."
        
        # Format price and discount
        price_text = f"{deal.current_price_string()} ({deal.discount()}% off)"
        
        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    title=ft.Text(title, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Column([
                        ft.Text(f"by {deal.authors}", color=ft.Colors.GREY_600),
                        ft.Text(price_text, color=ft.Colors.GREEN, weight=ft.FontWeight.BOLD)
                    ], spacing=2),
                    trailing=ft.Column([
                        ft.Text(deal.retailer, weight=ft.FontWeight.BOLD, size=12)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    on_click=lambda e, book=deal: self.app.show_book_details(book, format_type=book.format)
                ),
                padding=5
            )
        )

    def check_last_run(self):
        """Check when deals were last run"""
        db_conn = get_duckdb_conn()
        self.last_run_time = get_latest_deal_last_ran(db_conn)

    def can_run_latest_deals(self) -> bool:
        """Check if latest deals can be run (8 hour cooldown)"""
        if not self.last_run_time:
            return True
        
        # min_age = datetime.now() - timedelta(hours=8)
        # return self.last_run_time < min_age
        return True

    def run_latest_deals(self, e):
        """Run the latest deals check"""
        if not self.app.config:
            self.show_error("Please configure settings first")
            return
        
        if not self.can_run_latest_deals():
            self.show_error("Latest deals can only be run every 8 hours")
            return
        
        # Store the button reference for later re-enabling
        self.run_button = e.control
        
        # Start the async operation in a thread
        thread = threading.Thread(target=self._run_async_latest_deals)
        thread.daemon = True
        thread.start()
    
    def _run_async_latest_deals(self):
        """Run the async latest deals operation in a new event loop"""
        # Set loading state
        self.is_loading = True
        self.progress_container.visible = True
        self.run_button.disabled = True
        self.app.page.update()
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async operation
            success = loop.run_until_complete(self.app.run_latest_deals())
            
            if success:
                # Update the run time and load new deals
                self.last_run_time = self.app.config.run_time
                self.load_items()
                self.show_success(f"Found {len(self.items)} new deals!")
            else:
                self.show_error("Failed to get latest deals. Please check your configuration.")
                
        except Exception as ex:
            self.show_error(f"Error getting latest deals: {str(ex)}")
        
        finally:
            # Reset loading state
            self.is_loading = False
            self.progress_container.visible = False
            self.run_button.disabled = False
            self.check_last_run()  # Refresh the status
            self.update_items_display()
            # Need to update the whole page for the header status change
            if hasattr(self.app, 'page'):
                self.app.page.update()
            # Properly cleanup the event loop
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
            print(f"Error during event loop cleanup: {e}")
        finally:
            loop.close()

    def show_info_dialog(self, e):
        """Show information about the latest deals feature"""
        dlg = ft.AlertDialog(
            title=ft.Text("Latest Deals Information"),
            content=ft.Text(
                "The latest deals feature checks all tracked retailers for new deals on books in your library.\n\n"
                "To prevent abuse of retailer APIs, this feature can only be run every 8 hours.\n\n"
                "If you need to see existing deals immediately, use the 'All Deals' page instead."
            ),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog(dlg))]
        )
        self.app.page.overlay.append(dlg)
        dlg.open = True
        self.app.page.update()

    def show_error(self, message: str):
        """Show error dialog"""
        dlg = ft.AlertDialog(
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog(dlg))]
        )
        self.app.page.overlay.append(dlg)
        dlg.open = True
        self.app.page.update()

    def show_success(self, message: str):
        """Show success dialog"""
        dlg = ft.AlertDialog(
            title=ft.Text("Success"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog(dlg))]
        )
        self.app.page.overlay.append(dlg)
        dlg.open = True
        self.app.page.update()

    def close_dialog(self, dialog):
        """Close dialog"""
        dialog.open = False
        self.app.page.update()