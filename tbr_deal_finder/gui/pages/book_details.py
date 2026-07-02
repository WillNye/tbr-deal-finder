import logging
from collections import Counter

import flet as ft
from datetime import datetime, timedelta
from typing import List

from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.gui.widgets import cover_image_for_format, truncate_title
from tbr_deal_finder.utils import get_duckdb_conn, execute_query, float_to_currency

logger = logging.getLogger(__name__)


def build_book_price_section(max_dt: datetime, historical_data: list[dict]) -> ft.Column:
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
    window_start = (max_dt - timedelta(days=90)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    min_time = window_start.timestamp()
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
        if min_price is None or record["current_price"] < min_price:
            min_price = record["current_price"]
        if max_price is None or record["list_price"] > max_price:
            max_price = record["list_price"]

    for retailer, data in retailer_data.items():
        data["backfill"] = None
        points = data["data"]
        if not points or points[0].x <= min_time:
            continue
        first_point = points[0]
        pad_tooltip = f"{retailer}: {float_to_currency(first_point.y)} (before tracking)"
        data["backfill"] = [
            ft.LineChartDataPoint(min_time, first_point.y, tooltip=pad_tooltip),
            ft.LineChartDataPoint(first_point.x, first_point.y, tooltip=pad_tooltip),
        ]

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

    # X-axis setup - one label per month across the whole window, so the axis reflects the full ~90 days.
    x_axis_labels = []
    month_cursor = window_start
    while month_cursor <= max_dt:
        x_axis_labels.append(
            ft.ChartAxisLabel(
                value=month_cursor.timestamp(),
                label=ft.Text(month_cursor.strftime('%B'))
            )
        )
        if month_cursor.month == 12:
            month_cursor = month_cursor.replace(year=month_cursor.year + 1, month=1)
        else:
            month_cursor = month_cursor.replace(month=month_cursor.month + 1)

    data_series = []
    for retailer in retailer_data.values():
        if retailer["backfill"]:
            data_series.append(
                ft.LineChartData(
                    data_points=retailer["backfill"],
                    stroke_width=3,
                    color=ft.Colors.with_opacity(0.4, retailer["color"]),
                    curved=False,
                    stroke_cap_round=True,
                    dash_pattern=[4, 4],
                )
            )
        data_series.append(
            ft.LineChartData(
                data_points=retailer["data"],
                stroke_width=3,
                color=retailer["color"],
                curved=False,
                stroke_cap_round=True,
            )
        )

    # Create the chart
    chart = ft.LineChart(
        data_series=data_series,
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
        height=250,
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
            chart,
            ft.Container(
                content=legend,
                alignment=ft.alignment.center,
            ),
        ],
        spacing=15,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )


class BookDetailsPage:
    def __init__(self, app):
        self.app = app
        self.book = None
        self.selected_format = None  # Will be set when book is selected
        self.current_deals = []
        self.historical_data = []

    @staticmethod
    def page_id():
        return "book_details"
        
    def build(self):
        """Build the book details page content"""
        if not self.app.selected_book:
            return ft.Text("No book selected")
        
        self.book = self.app.selected_book
        
        # Set default format if not already set
        if self.selected_format is None:
            self.selected_format = self.get_default_format()
        
        self.load_book_data()
        header = self.build_header()

        # Historical pricing chart
        historical_chart = self.build_historical_chart()

        return ft.Column([
            header,
            ft.Divider(),
            historical_chart,
        ], spacing=20, scroll=ft.ScrollMode.AUTO)

    def build_header(self):
        """Build the header with back button and book title"""
        
        title = truncate_title(self.book.title, 80)

        # Create smaller back button
        back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Go back",
            on_click=self.go_back,
            icon_size=20,
            style=ft.ButtonStyle(
                color=ft.Colors.ON_SURFACE,
                overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)
            )
        )
        
        # Create copy button for title
        copy_button = ft.IconButton(
            icon=ft.Icons.COPY,
            tooltip="Copy title",
            on_click=self.copy_title,
            icon_size=20,
            style=ft.ButtonStyle(
                color=ft.Colors.ON_SURFACE,
                overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)
            )
        )
        
        cover = cover_image_for_format(self.book.image_url, self.selected_format, height=300)
        details = ft.Column([
            ft.Row([
                ft.Text(title, size=24, weight=ft.FontWeight.BOLD, selectable=True, expand=True),
                ft.Container(
                    content=copy_button,
                    padding=ft.padding.only(left=5)
                )
            ], spacing=0, alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Text(f"by {self.book.authors}", size=16, color=ft.Colors.GREY_600),
            self.build_format_selector(),
            self.build_price_summary_block(),
        ], spacing=5)
        current_pricing = self.build_current_pricing()

        stacked = self._is_stacked()
        self._last_stacked = stacked

        if stacked:
            body = ft.Column([
                ft.Row([cover]),
                details,
                current_pricing,
            ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        else:
            details.expand = True
            left_unit = ft.Row(
                [cover, details],
                spacing=30,
                vertical_alignment=ft.CrossAxisAlignment.START,
                expand=2,
            )
            current_pricing.expand = 3
            body = ft.Row(
                [left_unit, current_pricing],
                spacing=30,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

        return ft.Column([
            ft.Row([
                back_button
            ], alignment=ft.MainAxisAlignment.START),
            body,
        ], spacing=10)

    # Window width (px) below which the header stacks vertically.
    STACK_BELOW_WIDTH = 1750

    def _is_stacked(self) -> bool:
        page = getattr(self.app, "page", None)
        width = getattr(page, "width", None) if page else None
        return bool(width) and width < self.STACK_BELOW_WIDTH

    def handle_resize(self, e=None):
        """Rebuild the page only when crossing the stack threshold.

        Invoked by the app's global resize dispatcher for the visible page.
        """
        if self._is_stacked() != getattr(self, "_last_stacked", None):
            self.app.update_content()

    def build_price_summary_block(self):
        """Price summary heading with its stat rows indented beneath it, shown in the
        details column under the format."""
        return ft.Column([
            ft.Text("Price Summary", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column(self._price_summary_rows(), spacing=8),
                padding=ft.padding.only(left=15),
            ),
        ], spacing=8)

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
                padding=ft.padding.only(top=5)
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
            padding=ft.padding.only(top=5)
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
        """Build the Current Pricing section"""
        if not self.current_deals:
            body = ft.Text("No current deals available for this book", color=ft.Colors.GREY_600)
        else:
            cards = [self.create_retailer_card(deal) for deal in self.current_deals]
            body = ft.Row(
                cards,
                wrap=True,
                spacing=10,
                run_spacing=10,
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            )

        return ft.Container(
            content=ft.Column([
                ft.Text("Current Pricing", size=20, weight=ft.FontWeight.BOLD),
                body,
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
        chart_fig = build_book_price_section(self.app.get_last_run_time(), self.historical_data)

        return ft.Container(
            content=ft.Column([
                ft.Text("Historical Pricing", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Price trends over the last 3 months", color=ft.Colors.GREY_600),
                ft.Container(
                    content=chart_fig,
                    padding=ft.padding.symmetric(horizontal=60),
                ),
            ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

    def _price_summary_rows(self):
        """Agg pricing stat rows shown alongside the retailer price tiles."""
        if not self.current_deals:
            return [ft.Text("No pricing data available", color=ft.Colors.GREY_600)]

        prices = [deal.current_price for deal in self.current_deals]
        discounts = [deal.discount() for deal in self.current_deals]
        rows = []

        if len(prices) > 1:
            rows.append(self.create_info_row("Lowest Price", float_to_currency(min(prices))))
        else:
            rows.append(self.create_info_row("Current Price", float_to_currency(min(prices))))

        if self.has_historical_data():
            historical_prices = [retailer["current_price"] for retailer in self.historical_data]
            rows.append(self.create_info_row("Lowest Ever", float_to_currency(min(historical_prices))))

        if len(prices) > 1:
            rows.extend([
                self.create_info_row("Highest Price", float_to_currency(max(prices))),
                self.create_info_row("Best Discount", f"{max(discounts)}%"),
            ])

        rows.append(
            self.create_info_row("Available At", f"{len(self.current_deals)} retailer(s)")
        )
        return rows

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

    def copy_title(self, e=None):
        """Handle copy title button click"""
        try:
            # Copy the full title to clipboard
            self.app.page.set_clipboard(self.book.title)
            # Show a brief confirmation (you could add a snackbar here if desired)
            logger.info(f"Copied title to clipboard: {self.book.title}")
        except Exception as ex:
            logger.error(f"Failed to copy title to clipboard: {ex}")

    def go_back(self, e=None):
        """Handle back button click"""
        self.app.go_back()
