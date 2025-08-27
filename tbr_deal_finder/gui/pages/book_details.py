import logging

import flet as ft
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import List, Dict

from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.utils import get_duckdb_conn, execute_query

logger = logging.getLogger(__name__)

class BookDetailsPage:
    def __init__(self, app):
        self.app = app
        self.book = None
        self.selected_format = None  # Will be set when book is selected
        self.current_deals = []
        self.historical_data = []
        
    def build(self):
        """Build the book details page content"""
        if not self.app.selected_book:
            return ft.Text("No book selected")
        
        self.book = self.app.selected_book
        
        # Set default format if not already set
        if self.selected_format is None:
            self.selected_format = self.get_default_format()
        
        self.load_book_data()
        
        # Header with back button and book info
        header = self.build_header()
        
        # Format selector (always show prominently)
        format_selector = self.build_format_selector()
        
        # Current pricing section
        current_pricing = self.build_current_pricing()
        
        # Historical pricing chart
        historical_chart = self.build_historical_chart()
        
        # Book details section
        book_info = self.build_book_info()
        
        return ft.Column([
            header,
            format_selector,
            ft.Divider(),
            book_info,
            ft.Divider(),
            current_pricing,
            ft.Divider(),
            historical_chart,
        ], spacing=20, scroll=ft.ScrollMode.AUTO)

    def build_header(self):
        """Build the header with book title"""
        
        title = self.book.title
        if len(title) > 80:
            title = f"{title[:80]}..."
        
        return ft.Row([
            ft.Column([
                ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"by {self.book.authors}", size=16, color=ft.Colors.GREY_600)
            ], spacing=5, expand=True)
        ], alignment=ft.MainAxisAlignment.START)

    def get_default_format(self) -> BookFormat:
        """Get the default format for this book, preferring audiobook"""
        # Check what formats are available for this book
        available_formats = self.get_available_formats()
        
        # Prefer audiobook if available, otherwise use ebook
        if BookFormat.AUDIOBOOK in available_formats:
            return BookFormat.AUDIOBOOK
        elif BookFormat.EBOOK in available_formats:
            return BookFormat.EBOOK
        else:
            # Fallback to the book's original format
            return self.book.format

    def get_available_formats(self) -> List[BookFormat]:
        """Get list of formats available for this book"""
        db_conn = get_duckdb_conn()
        
        query = """
        SELECT DISTINCT format
        FROM retailer_deal
        WHERE title = ? AND authors = ? AND deleted IS NOT TRUE
        """
        
        try:
            results = execute_query(db_conn, query, [self.book.title, self.book.authors])
            formats = []
            for row in results:
                try:
                    formats.append(BookFormat(row['format']))
                except ValueError:
                    continue  # Skip invalid format values
            return formats
        except Exception as e:
            logger.info(f"Error getting available formats: {e}")
            return [self.book.format]  # Fallback to original format

    def build_format_selector(self):
        """Build format selector with text display and dropdown"""
        available_formats = self.get_available_formats()
        logger.info(f"Available formats for {self.book.title}: {[f.value for f in available_formats]}")
        logger.info(f"Currently selected format: {self.selected_format.value if self.selected_format else 'None'}")

        format_text_str = "Format: "
        if len(available_formats) <= 1:
            format_text_str = f"{format_text_str}{self.selected_format.value}"

        # Current format display text
        format_text = ft.Text(
            format_text_str,
            size=18,
            weight=ft.FontWeight.BOLD
        )
        
        if len(available_formats) <= 1:
            # Only one format available, just show the text
            return ft.Container(
                content=format_text,
                padding=ft.padding.symmetric(0, 10)
            )
        
        # Multiple formats available, show text + dropdown
        format_options = []
        for format_type in available_formats:
            format_options.append(
                ft.dropdown.Option(
                    key=format_type.value,
                    text=format_type.value
                )
            )
        
        format_dropdown = ft.Dropdown(
            value=self.selected_format.value,
            options=format_options,
            on_change=self.on_format_changed,
            width=200,
            menu_height=80,
            max_menu_height=80
        )
        
        return ft.Container(
            content=ft.Row([
                format_text,
                format_dropdown
            ], spacing=20, alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(10, 10)
        )

    def create_format_badge(self, format_type: BookFormat):
        """Create a format badge"""
        color = ft.Colors.BLUE if format_type == BookFormat.EBOOK else ft.Colors.GREEN
        return ft.Container(
            content=ft.Text(
                format_type.value,
                size=12,
                color=ft.Colors.WHITE,
                weight=ft.FontWeight.BOLD
            ),
            bgcolor=color,
            border_radius=12,
            padding=ft.padding.symmetric(12, 6),
            alignment=ft.alignment.center
        )

    def on_format_changed(self, e):
        """Handle format selection change"""
        new_format = BookFormat(e.control.value)
        logger.info(f"Format changed to: {new_format.value}")
        if new_format != self.selected_format:
            self.selected_format = new_format
            self.refresh_format_data()

    def refresh_format_data(self):
        """Refresh data for the new format without rebuilding entire page"""
        logger.info(f"Refreshing data for format: {self.selected_format.value}")
        # Reload data for the new format
        self.load_book_data()
        # Rebuild the page content
        self.app.update_content()

    def set_initial_format(self, format_type: BookFormat):
        """Set the initial format to display"""
        self.selected_format = format_type

    def build_current_pricing(self):
        """Build current pricing information section"""
        if not self.current_deals:
            return ft.Container(
                content=ft.Column([
                    ft.Text("Current Pricing", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("No current deals available for this book", color=ft.Colors.GREY_600)
                ]),
                padding=20,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=8
            )
        
        # Group deals by retailer
        retailer_cards = []
        for deal in self.current_deals:
            card = self.create_retailer_card(deal)
            retailer_cards.append(card)
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Current Pricing", size=20, weight=ft.FontWeight.BOLD),
                ft.Text(f"Showing prices for {len(retailer_cards)} retailer(s)", color=ft.Colors.GREY_600),
                ft.Row(retailer_cards, wrap=True, spacing=10)
            ], spacing=15),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

    def create_retailer_card(self, deal: Book):
        """Create a card for a retailer's pricing"""
        # Calculate discount color
        discount = deal.discount()
        if discount >= 50:
            discount_color = ft.Colors.GREEN
        elif discount >= 30:
            discount_color = ft.Colors.ORANGE
        else:
            discount_color = ft.Colors.RED
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(deal.retailer, weight=ft.FontWeight.BOLD, size=16),
                    ft.Text(
                        deal.current_price_string(),
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN
                    ),
                    ft.Text(f"was {deal.list_price_string()}", color=ft.Colors.GREY_500),
                    ft.Container(
                        content=ft.Text(
                            f"{discount}% OFF",
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD,
                            size=12
                        ),
                        bgcolor=discount_color,
                        border_radius=8,
                        padding=ft.padding.symmetric(8, 4),
                        alignment=ft.alignment.center
                    )
                ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15,
                width=150
            )
        )

    def build_historical_chart(self):
        """Build historical pricing chart"""
        if not self.historical_data:
            return ft.Container(
                content=ft.Column([
                    ft.Text("Historical Pricing", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("No historical data available", color=ft.Colors.GREY_600)
                ]),
                padding=20,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=8
            )
        
        # Create the chart
        chart_html = self.create_pricing_chart()
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Historical Pricing", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Price trends over the last 90 days", color=ft.Colors.GREY_600),
                ft.Container(
                    content=ft.Text("Chart would be displayed here (HTML/Plotly integration needed)", 
                                   color=ft.Colors.GREY_500),
                    height=300,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=8,
                    alignment=ft.alignment.center
                )
                # Note: Flet has limited Plotly integration. In a real implementation,
                # you might use ft.PlotlyChart or save as image and display
            ], spacing=15),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

    def build_book_info(self):
        """Build book information section"""
        info_items = []
        
        # Basic info
        info_items.extend([
            self.create_info_row("Title", self.book.title),
            self.create_info_row("Author(s)", self.book.authors),
            self.create_info_row("Format", self.selected_format.value)
        ])
        
        # Price statistics from current deals
        if self.current_deals:
            prices = [deal.current_price for deal in self.current_deals]
            discounts = [deal.discount() for deal in self.current_deals]
            
            info_items.extend([
                self.create_info_row("Lowest Price", f"${min(prices):.2f}"),
                self.create_info_row("Highest Price", f"${max(prices):.2f}"),
                self.create_info_row("Best Discount", f"{max(discounts)}%"),
                self.create_info_row("Available At", f"{len(self.current_deals)} retailer(s)")
            ])
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Book Information", size=20, weight=ft.FontWeight.BOLD),
                ft.Column(info_items, spacing=8)
            ], spacing=15),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

    def create_info_row(self, label: str, value: str):
        """Create an information row"""
        return ft.Row([
            ft.Text(f"{label}:", weight=ft.FontWeight.BOLD, width=150),
            ft.Text(value, expand=True)
        ])

    def load_book_data(self):
        """Load current deals and historical data for the book"""
        try:
            self.load_current_deals()
            self.load_historical_data()
        except Exception as e:
            logger.info(f"Error loading book data: {e}")
            self.current_deals = []
            self.historical_data = []

    def load_current_deals(self):
        """Load current active deals for this book in the selected format"""
        db_conn = get_duckdb_conn()
        
        # Get current deals for this specific book and format
        query = """
        SELECT * exclude(deal_id)
        FROM retailer_deal
        WHERE title = ? AND authors = ? AND format = ?
        QUALIFY ROW_NUMBER() OVER (PARTITION BY retailer ORDER BY timepoint DESC) = 1 
        AND deleted IS NOT TRUE
        ORDER BY current_price ASC
        """
        
        results = execute_query(
            db_conn,
            query,
            [self.book.title, self.book.authors, self.selected_format.value]
        )
        
        self.current_deals = [Book(**deal) for deal in results]

    def load_historical_data(self):
        """Load historical pricing data for this book in the selected format"""
        db_conn = get_duckdb_conn()
        
        # Get historical data for the last 90 days
        cutoff_date = datetime.now() - timedelta(days=90)
        
        query = """
        SELECT retailer, current_price, timepoint
        FROM retailer_deal
        WHERE title = ? AND authors = ? AND format = ? 
        AND timepoint >= ? AND deleted IS NOT TRUE
        ORDER BY timepoint ASC
        """
        
        results = execute_query(
            db_conn,
            query,
            [self.book.title, self.book.authors, self.selected_format.value, cutoff_date]
        )
        
        self.historical_data = results

    def create_pricing_chart(self):
        """Create a Plotly chart for historical pricing"""
        if not self.historical_data:
            return ""
        
        # Group data by retailer
        retailer_data = {}
        for row in self.historical_data:
            retailer = row['retailer']
            if retailer not in retailer_data:
                retailer_data[retailer] = {'dates': [], 'prices': []}
            retailer_data[retailer]['dates'].append(row['timepoint'])
            retailer_data[retailer]['prices'].append(row['current_price'])
        
        # Create Plotly figure
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        for i, (retailer, data) in enumerate(retailer_data.items()):
            fig.add_trace(go.Scatter(
                x=data['dates'],
                y=data['prices'],
                mode='lines+markers',
                name=retailer,
                line=dict(color=colors[i % len(colors)])
            ))
        
        fig.update_layout(
            title=f"Price History - {self.book.title} ({self.selected_format.value})",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            hovermode='x unified',
            height=300
        )
        
        # Convert to HTML (this would need to be integrated with Flet's plotting capabilities)
        return fig.to_html()

    def refresh_data(self):
        """Refresh book data"""
        self.load_book_data()
        self.app.update_content()
