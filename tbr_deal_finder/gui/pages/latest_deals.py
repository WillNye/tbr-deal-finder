import flet as ft
from datetime import datetime, timedelta
from typing import List

from tbr_deal_finder.book import get_deals_found_at, Book, BookFormat, is_qualifying_deal
from tbr_deal_finder.utils import get_duckdb_conn, get_latest_deal_last_ran
from tbr_deal_finder.gui.pages.base_book_page import BaseBookPage


class LatestDealsPage(BaseBookPage):
    def __init__(self, app):
        super().__init__(app, 4)
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
        # Items list container that we can update without rebuilding search controls
        self.items_container = ft.Container()
        self.pagination_container = ft.Container()
        
        # Initial build of items and pagination
        self.update_items_display()
        
        return ft.Column([
            self.items_container,
            self.pagination_container
        ], spacing=20)

    def build_items_list(self):
        """Override base class to handle format grouping with proper pagination"""
        if self.is_loading:
            return ft.Container()
        
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
        
        # Apply pagination to all filtered items
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.filtered_items))
        page_items = self.filtered_items[start_idx:end_idx]
        
        # Group page items by format for better organization
        ebooks = [deal for deal in page_items if deal.format == BookFormat.EBOOK]
        audiobooks = [deal for deal in page_items if deal.format == BookFormat.AUDIOBOOK]
        
        sections = []
        
        if ebooks:
            sections.append(self.build_format_section("E-Book Deals", ebooks))
        
        if audiobooks:
            sections.append(self.build_format_section("Audiobook Deals", audiobooks))
        
        if not sections:
            return ft.Container()
        
        return ft.Container(
            content=ft.Column(sections, spacing=20),
            padding=10
        )

    def build_format_section(self, title: str, deals: List[Book]):
        """Build a section for a specific format (without pagination - that's handled at the page level)"""
        deals_tiles = []
        current_title_id = None
        for deal in deals:
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
        if not self.last_run_time:
            db_conn = get_duckdb_conn()
            self.last_run_time = get_latest_deal_last_ran(db_conn)

    def can_run_latest_deals(self) -> bool:
        """Check if latest deals can be run (8 hour cooldown)"""
        if not self.last_run_time:
            return True
        
        min_age = datetime.now() - timedelta(hours=8)
        return self.last_run_time < min_age

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
        
        # Use Flet's proper async task runner instead of threading
        self.app.page.run_task(self._run_async_latest_deals)
    
    async def _run_async_latest_deals(self):
        """Run the async latest deals operation using Flet's async support"""
        # Set loading state
        self.is_loading = True
        self.progress_container.visible = True
        self.run_button.disabled = True
        
        # Disable navigation during the operation
        self.app.disable_navigation()
        
        # Update the page to show loading state
        self.app.page.update()
        
        try:
            # Run the async operation directly (no need for new event loop)
            success = await self.app.run_latest_deals()
            
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
            
            # Re-enable navigation after the operation
            self.app.enable_navigation()
            
            # Update the page to reset loading state
            self.app.page.update()
            
            # Refresh all pages since latest deals affects data on other pages
            self.app.refresh_all_pages()
            # Force a full page rebuild to update header status and content
            self.app.update_content()


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
    
    def refresh_page_state(self):
        """Override base refresh to handle latest deals specific state"""
        # Reset state
        self.items = []
        self.filtered_items = []
        self.current_page = 0
        self.search_query = ""
        self.format_filter = "All"
        
        # Reset UI elements if they exist
        if hasattr(self, 'search_field'):
            self.search_field.value = ""
        if hasattr(self, 'format_dropdown'):
            self.format_dropdown.value = "All"
        
        # Check last run and reload data
        self.check_last_run()
        self.load_items()