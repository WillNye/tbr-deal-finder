import logging
from collections import Counter

import flet as ft
from datetime import datetime, timedelta
from typing import List

from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.utils import get_duckdb_conn, execute_query, float_to_currency

logger = logging.getLogger(__name__)


def build_book_price_section(historical_data: list[dict]) -> ft.Column:
    retailer_data = dict()
    available_colors = [
        ft.Colors.AMBER,
        ft.Colors.INDIGO,
        ft.Colors.CYAN,
        ft.Colors.ORANGE,
        ft.Colors.RED,
        ft.Colors.GREEN,
        ft.Colors.YELLOW,
        ft.Colors.BLUE,
    ]

    min_price = None
    max_price = None
    min_time = None
    max_dt = datetime.now()
    max_time = max_dt.timestamp()

    for record in historical_data:
        if record["retailer"] not in retailer_data:
            retailer_data[record["retailer"]] = dict()
            retailer_data[record["retailer"]]["color"] = available_colors.pop(0)
            retailer_data[record["retailer"]]["data"] = []
            retailer_data[record["retailer"]]["last_update"] = None

        # Convert datetime to timestamp for x-axis
        timestamp = record["timepoint"].timestamp()
        tooltip = f"{record['retailer']}: {float_to_currency(record['current_price'])}"

        if last_update := retailer_data[record["retailer"]]["last_update"]:
            max_update_marker = last_update["timepoint"] + timedelta(days=1)
            last_price = last_update["current_price"]
            pad_tooltip = f"{record['retailer']}: {float_to_currency(last_price)}"
            # Padding to show more consistent info on graph hover
            while record["timepoint"] > max_update_marker:
                retailer_data[record["retailer"]]["data"].append(
                    ft.LineChartDataPoint(max_update_marker.timestamp(), last_price, tooltip=pad_tooltip)
                )
                max_update_marker = max_update_marker + timedelta(days=1)

        retailer_data[record["retailer"]]["last_update"] = record
        retailer_data[record["retailer"]]["data"].append(
            ft.LineChartDataPoint(timestamp, record["current_price"], tooltip=tooltip)
        )

        # Track price range
        if not min_price or record["current_price"] < min_price:
            min_price = record["current_price"]
        if not max_price or record["list_price"] > max_price:
            max_price = record["list_price"]

        # Track time range
        if not min_time or timestamp < min_time:
            min_time = timestamp

    # Add hover padding to current date
    for retailer, data in retailer_data.items():
        last_update = data["last_update"]
        max_update_marker = last_update["timepoint"] + timedelta(days=1)
        last_price = last_update["current_price"]
        pad_tooltip = f"{retailer}: {float_to_currency(last_price)}"
        # Padding to show more consistent info on graph hover
        while max_dt > (max_update_marker + timedelta(hours=6)):
            max_update_marker_ts = max_update_marker.timestamp()
            data["data"].append(
                ft.LineChartDataPoint(max_update_marker_ts, last_price, tooltip=pad_tooltip)
            )
            data["last_update"]["timepoint"] = max_update_marker

            max_update_marker = max_update_marker + timedelta(days=1)

    # Add data point if one doesn't exist for max time so lines don't just end abruptly
    for retailer, data in retailer_data.items():
        last_update = data["last_update"]
        last_entry = last_update["timepoint"].timestamp()
        if last_entry == max_time:
            continue

        last_price = last_update["current_price"]
        pad_tooltip = f"{retailer}: {float_to_currency(last_price)}"
        data["data"].append(
            ft.LineChartDataPoint(max_time, last_price, tooltip=pad_tooltip)
        )

    # Y-axis setup
    y_min = min_price // 5 * 5  # Keep as float
    y_max = ((max_price + 4) // 5) * 5  # Round up to nearest 5
    y_axis_labels = []
    for val in range(int(y_min), int(y_max) + 1, 5):
        y_axis_labels.append(
            ft.ChartAxisLabel(
                value=val,
                label=ft.Text(float_to_currency(val), no_wrap=True)
            )
        )

    # X-axis setup - create labels for actual data points
    x_axis_labels = []

    # Get unique months from the data
    unique_months = set()
    for record in historical_data:
        timepoint = record["timepoint"].replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_year = timepoint.strftime('%B %Y')
        unique_months.add((timepoint.timestamp(), month_year))

    # Sort by timestamp and create labels
    for timestamp, month_year in sorted(unique_months):
        date_str = month_year.split()[0]  # Just show month abbreviation
        x_axis_labels.append(
            ft.ChartAxisLabel(
                value=timestamp,
                label=ft.Container(
                    content=ft.Text(date_str),
                    padding=ft.padding.only(left=20)  # Add top padding
                )
            )
        )

    # Create the chart
    chart = ft.LineChart(
        data_series=[
            ft.LineChartData(
                data_points=retailer["data"],
                stroke_width=3,
                color=retailer["color"],
                curved=True,
                stroke_cap_round=True,
            )
            for retailer in retailer_data.values()
        ],
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
        horizontal_grid_lines=ft.ChartGridLines(
            interval=5,
            color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE),
            width=1,
        ),
        vertical_grid_lines=ft.ChartGridLines(
            interval=604800,  # 1 week
            color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE),
            width=1,
        ),
        left_axis=ft.ChartAxis(labels=y_axis_labels, labels_size=50),
        bottom_axis=ft.ChartAxis(labels=x_axis_labels, labels_interval=3600),  # 1 hour
        expand=False,
        height=200,
        width=850,
        min_x=min_time,
        max_x=max_time,
        min_y=y_min,
        max_y=y_max,
        interactive=True,
    )

    # Legend
    row_data = []
    for retailer_name, retailer in retailer_data.items():
        row_data.append(
            ft.Row([
                ft.Container(width=20, height=3, bgcolor=retailer["color"]),
                ft.Text(retailer_name),
            ], spacing=5),
        )
    legend = ft.Row(row_data, spacing=20)

    return ft.Column(
        [
            ft.Container(
                content=chart,
                padding=25,
            ),
            ft.Container(
                content=legend,
                alignment=ft.alignment.center,
            ),
        ],
        spacing=0
    )


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
        if not self.has_historical_data():
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
        chart_fig = build_book_price_section(self.historical_data)
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Historical Pricing", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Price trends over the last 3 months", color=ft.Colors.GREY_600),
                ft.Container(
                    content=chart_fig,
                    height=300,
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


            if len(prices) > 1:
                info_items.append(self.create_info_row("Lowest Price", f"${min(prices):.2f}"))
            else:
                info_items.append(self.create_info_row("Current Price", f"${min(prices):.2f}"))

            if self.has_historical_data():
                historical_prices = [retailer["current_price"] for retailer in self.historical_data]
                lowest_ever_price = min(historical_prices)
                info_items.append(self.create_info_row("Lowest Ever", f"${lowest_ever_price:.2f}"))

            if len(prices) > 1:
                info_items.extend([
                    self.create_info_row("Highest Price", f"${max(prices):.2f}"),
                    self.create_info_row("Best Discount", f"{max(discounts)}%"),
                ])

            info_items.append(
                self.create_info_row("Available At", f"{len(self.current_deals)} retailer(s)")
            )
        
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
        SELECT retailer, list_price, current_price, timepoint
        FROM retailer_deal
        WHERE title = ? AND authors = ? AND format = ? 
        AND timepoint >= ?
        ORDER BY timepoint ASC
        """
        
        results = execute_query(
            db_conn,
            query,
            [self.book.title, self.book.authors, self.selected_format.value, cutoff_date]
        )
        
        self.historical_data = results

    def has_historical_data(self) -> bool:
        """Returns True if at least one retailer has more than 1 record in retailer_deal"""
        if not self.historical_data:
            return False

        retailer_refs = [deal["retailer"] for deal in self.historical_data]
        retailer_counts = Counter(retailer_refs)
        return any(rc > 1 for rc in retailer_counts.values())

    def refresh_data(self):
        """Refresh book data"""
        self.load_book_data()
        self.app.update_content()
