import flet as ft
from abc import ABC, abstractmethod
from typing import List, Any

from tbr_deal_finder.book import Book, BookFormat


class BaseBookPage(ABC):
    """Base class for pages that display lists of books with pagination, search, and filtering."""
    
    def __init__(self, app, items_per_page: int):
        self.app = app
        self.items = []
        self.filtered_items = []
        self.current_page = 0
        self.items_per_page = items_per_page
        self.search_query = ""
        self.format_filter = "All"
        self.is_loading = False
        
    @abstractmethod
    def get_page_title(self) -> str:
        """Return the page title."""
        pass
    
    @abstractmethod
    def load_items(self):
        """Load items from data source. Should set self.items and call apply_filters()."""
        pass
    
    @abstractmethod
    def create_item_tile(self, item: Any) -> ft.Control:
        """Create a tile for a single item."""
        pass
    
    @abstractmethod
    def get_empty_state_message(self) -> tuple[str, str]:
        """Return (main_message, sub_message) for empty state."""
        pass
    
    def get_format_filter_options(self) -> List[str]:
        """Return available format filter options. Override if needed."""
        return ["All", "E-Book", "Audiobook"]
    
    def should_include_refresh_button(self) -> bool:
        """Whether to include a refresh button. Override if needed."""
        return True
    
    def build(self):
        """Build the page content"""
        # Search and filter controls
        search_controls = self.build_search_controls()
        
        # Loading indicator
        self.loading_container = ft.Container(
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Loading...", text_align=ft.TextAlign.CENTER),
                ft.Text(
                    "Syncing and retrieving your TBR.\nThis may take a few minutes if you've recently made changes to your wishlist, exports, or this is your first time.",
                    text_align=ft.TextAlign.CENTER,
                    size=11
                )
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            visible=self.is_loading,
            alignment=ft.alignment.center,
            height=200
        )

        if not self.items and not self.is_loading:
            self.load_items()
        
        # Items list container that we can update without rebuilding search controls
        self.items_container = ft.Container()
        self.pagination_container = ft.Container()
        
        # Initial build of items and pagination
        self.update_items_display()
        
        return ft.Column([
            ft.Text(self.get_page_title(), size=24, weight=ft.FontWeight.BOLD),
            search_controls,
            self.loading_container,
            self.items_container,
            self.pagination_container
        ], spacing=20, scroll=ft.ScrollMode.AUTO)

    def build_search_controls(self):
        """Build search and filter controls"""
        self.search_field = ft.TextField(
            label="Search...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self.on_search_change,
            value=self.search_query,
            expand=True
        )
        
        self.format_dropdown = ft.Dropdown(
            label="Format",
            value=self.format_filter,
            options=[ft.dropdown.Option(option) for option in self.get_format_filter_options()],
            on_change=self.on_format_change,
            width=150
        )
        
        controls = [self.search_field, self.format_dropdown]
        
        if self.should_include_refresh_button():
            refresh_button = ft.IconButton(
                icon=ft.Icons.REFRESH,
                tooltip="Refresh",
                on_click=self.refresh_items
            )
            controls.append(refresh_button)
        
        return ft.Row(controls, spacing=10)

    def build_items_list(self):
        """Build the items list with current page items"""
        if self.is_loading:
            return ft.Container()
        
        if not self.filtered_items:
            main_msg, sub_msg = self.get_empty_state_message()
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SEARCH_OFF, size=64, color=ft.Colors.GREY_400),
                    ft.Text(main_msg, size=18, color=ft.Colors.GREY_600),
                    ft.Text(sub_msg, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                height=300
            )
        
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.filtered_items))
        page_items = self.filtered_items[start_idx:end_idx]
        
        item_tiles = []
        for item in page_items:
            tile = self.create_item_tile(item)
            item_tiles.append(tile)
        
        return ft.Container(
            content=ft.Column(item_tiles, spacing=5),
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
            padding=10
        )

    def build_pagination(self):
        """Build pagination controls"""
        if not self.filtered_items or self.is_loading:
            return ft.Container()
        
        total_pages = (len(self.filtered_items) + self.items_per_page - 1) // self.items_per_page
        
        # Page info
        start_item = self.current_page * self.items_per_page + 1
        end_item = min((self.current_page + 1) * self.items_per_page, len(self.filtered_items))
        
        page_info = ft.Text(
            f"Showing {start_item}-{end_item} of {len(self.filtered_items)} items",
            color=ft.Colors.GREY_600
        )
        
        # Navigation buttons
        prev_button = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT,
            on_click=self.prev_page,
            disabled=self.current_page == 0
        )
        
        next_button = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT,
            on_click=self.next_page,
            disabled=self.current_page >= total_pages - 1
        )
        
        page_number = ft.Text(
            f"Page {self.current_page + 1} of {total_pages}",
            weight=ft.FontWeight.BOLD
        )
        
        return ft.Row([
            page_info,
            ft.Row([prev_button, page_number, next_button], spacing=5)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def apply_filters(self):
        """Apply search and format filters"""
        filtered = self.items
        
        # Apply search filter
        if self.search_query:
            filtered = self.filter_by_search(filtered, self.search_query)
        
        # Apply format filter
        if self.format_filter != "All":
            filtered = self.filter_by_format(filtered, self.format_filter)
        
        # Apply custom sorting
        self.filtered_items = self.sort_items(filtered)
        self.current_page = 0  # Reset to first page when filters change

    def filter_by_search(self, items: List[Book], query: str) -> List[Book]:
        """Filter items by search query. Override if needed."""
        query = query.lower()
        return [
            item for item in items
            if query in item.title.lower() or query in str(item.normalized_authors)
        ]

    def filter_by_format(self, items: List[Book], format_filter: str) -> List[Book]:
        """Filter items by format. Override if needed."""
        if format_filter == "E-Book":
            format_value = BookFormat.EBOOK
        elif format_filter == "Audiobook":
            format_value = BookFormat.AUDIOBOOK
        else:
            return items
        
        return [item for item in items if item.format == format_value]

    def sort_items(self, items: List[Book]) -> List[Book]:
        """Sort items. Override to customize sorting."""
        return sorted(items, key=lambda x: x.deal_id)

    def on_search_change(self, e):
        """Handle search query changes"""
        self.search_query = e.control.value
        self.apply_filters()
        self.update_items_display()

    def on_format_change(self, e):
        """Handle format filter changes"""
        self.format_filter = e.control.value
        self.apply_filters()
        self.update_items_display()

    def refresh_items(self, e):
        """Refresh the items list"""
        self.load_items()
        self.update_items_display()

    def prev_page(self, e):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_items_display()

    def next_page(self, e):
        """Go to next page"""
        total_pages = (len(self.filtered_items) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_items_display()

    def update_items_display(self):
        """Update only the items list and pagination, preserving search field state"""
        if hasattr(self, 'items_container') and hasattr(self, 'pagination_container'):
            self.items_container.content = self.build_items_list()
            self.pagination_container.content = self.build_pagination()
            if self.app and hasattr(self.app, 'page'):
                self.app.page.update()

    def set_loading(self, loading: bool):
        """Set loading state and update UI"""
        self.is_loading = loading
        if hasattr(self, 'loading_container'):
            self.loading_container.visible = loading
        self.update_items_display()
    
    def refresh_page_state(self):
        """Clear page state and reload data. Called when navigating to this page."""
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
        
        # Reload data
        self.load_items()