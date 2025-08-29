import asyncio
import os

import flet as ft

from tbr_deal_finder.config import Config
from tbr_deal_finder.book import Book, BookFormat
from tbr_deal_finder.retailer import RETAILER_MAP
from tbr_deal_finder.retailer.models import Retailer
from tbr_deal_finder.retailer_deal import get_latest_deals
from tbr_deal_finder.desktop_updater import check_for_desktop_updates

from tbr_deal_finder.gui.pages.settings import SettingsPage
from tbr_deal_finder.gui.pages.all_deals import AllDealsPage
from tbr_deal_finder.gui.pages.latest_deals import LatestDealsPage
from tbr_deal_finder.gui.pages.all_books import AllBooksPage
from tbr_deal_finder.gui.pages.book_details import BookDetailsPage


class TBRDealFinderApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.config = None
        self.current_page = "all_deals"
        self.selected_book = None
        self.update_info = None  # Store update information
        
        # Initialize pages
        self.settings_page = SettingsPage(self)
        self.all_deals_page = AllDealsPage(self)
        self.latest_deals_page = LatestDealsPage(self)
        self.all_books_page = AllBooksPage(self)
        self.book_details_page = BookDetailsPage(self)
        
        self.setup_page()
        self.load_config()
        self.build_layout()

    def setup_page(self):
        """Configure the main page settings"""
        self.page.title = "TBR Deal Finder"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.spacing = 0
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.window.min_width = 800
        self.page.window.min_height = 600

    def load_config(self):
        """Load configuration or create default"""
        try:
            self.config = Config.load()
        except FileNotFoundError:
            # Will prompt for config setup
            self.config = None

    def build_layout(self):
        """Build the main application layout"""
        # Top app bar with settings cog
        app_bar = ft.AppBar(
            title=ft.Text("TBR Deal Finder", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE60),
            center_title=False,
            bgcolor=ft.Colors.BLUE_GREY_900,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    tooltip="Settings",
                    on_click=self.show_settings
                )
            ]
        )

        # Navigation rail (left sidebar)
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=200,
            min_extended_width=200,
            group_alignment=-1.0,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.LOCAL_OFFER,
                    selected_icon=ft.Icons.LOCAL_OFFER_OUTLINED,
                    label="All Deals"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.NEW_RELEASES,
                    selected_icon=ft.Icons.NEW_RELEASES_OUTLINED,
                    label="Latest Deals"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIBRARY_BOOKS,
                    selected_icon=ft.Icons.LIBRARY_BOOKS_OUTLINED,
                    label="My Books"
                ),
            ],
            on_change=self.nav_changed
        )

        # Main content area
        self.content_area = ft.Container(
            content=self.get_current_page_content(),
            expand=True,
            padding=20
        )

        # Main layout with sidebar and content
        main_layout = ft.Row(
            [
                self.nav_rail,
                ft.VerticalDivider(width=1),
                self.content_area
            ],
            expand=True,
            spacing=0
        )

        # Add everything to page
        self.page.appbar = app_bar
        self.page.add(main_layout)
        self.page.update()

    def nav_changed(self, e):
        """Handle navigation rail selection changes"""
        destinations = ["all_deals", "latest_deals", "all_books"]
        if e.control.selected_index < len(destinations):
            self.current_page = destinations[e.control.selected_index]
            self.update_content()

    def update_content(self):
        """Update the main content area"""
        self.content_area.content = self.get_current_page_content()
        self.page.update()

    def get_current_page_content(self):
        """Get content for the current page"""
        if self.config is None and self.current_page != "settings":
            return self.get_config_prompt()
        
        if self.current_page == "all_deals":
            return self.all_deals_page.build()
        elif self.current_page == "latest_deals":
            return self.latest_deals_page.build()
        elif self.current_page == "all_books":
            return self.all_books_page.build()
        elif self.current_page == "book_details":
            return self.book_details_page.build()
        elif self.current_page == "settings":
            return self.settings_page.build()
        else:
            return ft.Text("Page not found")

    def get_config_prompt(self):
        """Show config setup prompt when no config exists"""
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.SETTINGS, size=64, color=ft.Colors.GREY_400),
                ft.Text(
                    "Welcome to TBR Deal Finder!",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "You need to configure your settings before getting started.",
                    size=16,
                    color=ft.Colors.GREY_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.ElevatedButton(
                    "Configure Settings",
                    icon=ft.Icons.SETTINGS,
                    on_click=self.show_settings
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20),
            alignment=ft.alignment.center
        )

    def show_settings(self, e=None):
        """Show settings page"""
        self.current_page = "settings"
        self.nav_rail.selected_index = None  # Deselect nav items
        self.update_content()

    def show_book_details(self, book: Book, format_type: BookFormat = None):
        """Show book details page"""
        self.selected_book = book
        
        # Set the initial format if specified
        if format_type is not None and format_type != BookFormat.NA:
            self.book_details_page.set_initial_format(format_type)
        else:
            # Reset selected format so it uses default logic
            self.book_details_page.selected_format = None
        
        self.current_page = "book_details"
        self.nav_rail.selected_index = None
        self.update_content()

    def go_back_to_deals(self):
        """Return to deals page from book details"""
        self.current_page = "all_deals"
        self.nav_rail.selected_index = 0
        self.update_content()

    def config_updated(self, new_config: Config):
        """Handle config updates"""
        self.config = new_config
        if self.current_page == "settings":
            self.current_page = "all_deals"
            self.nav_rail.selected_index = 0
        self.update_content()

    async def run_latest_deals(self):
        """Run the latest deals check with progress tracking using GUI auth"""
        if not self.config:
            return False
        
        try:
            # First authenticate all retailers using GUI dialogs
            await self.auth_all_configured_retailers()
            # Then fetch the deals (retailers should already be authenticated)
            return await get_latest_deals(self.config)
        except Exception as e:
            return False

    async def auth_all_configured_retailers(self):
        for retailer_str in self.config.tracked_retailers:
            retailer = RETAILER_MAP[retailer_str]()

            # Skip if already authenticated
            if retailer.user_is_authed():
                continue

            # Use GUI auth instead of CLI auth
            await self.show_auth_dialog(retailer)

    async def show_auth_dialog(self, retailer: Retailer):
        """Show authentication dialog for retailer login"""

        auth_context = retailer.gui_auth_context
        title = auth_context.title
        fields = auth_context.fields
        message = auth_context.message
        user_copy_context = auth_context.user_copy_context
        pop_up_type = auth_context.pop_up_type

        # Store the dialog reference at instance level temporarily
        self._auth_dialog_result = None
        self._auth_dialog_complete = False

        def close_dialog():
            dialog.open = False
            self.page.update()

        async def handle_submit(e=None):
            form_data = {}
            for field in fields:
                field_name = field["name"]
                field_ref = field.get("ref")
                if field_ref:
                    form_data[field_name] = field_ref.value

            try:
                result = await retailer.gui_auth(form_data)
                if result:
                    close_dialog()
                    self._auth_dialog_result = True
                    self._auth_dialog_complete = True
                else:
                    # Show error in dialog
                    error_text.value = "Login failed, please try again"
                    error_text.visible = True
                    self.page.update()
            except Exception as ex:
                self._auth_dialog_result = False
                self._auth_dialog_complete = True

        # Build dialog with error text
        error_text = ft.Text("", color=ft.Colors.RED, visible=False)
        content_controls = [error_text]

        if message:
            content_controls.append(
                ft.Text(message, selectable=True)
            )
        
        # Add user copy context if available
        if user_copy_context:
            def copy_to_clipboard(e):
                self.page.set_clipboard(user_copy_context)
                copy_button.text = "Copied!"
                copy_button.icon = ft.Icons.CHECK
                self.page.update()
                # Reset button after 2 seconds
                import threading
                def reset_button():
                    import time
                    time.sleep(.25)
                    copy_button.text = "Copy"
                    copy_button.icon = ft.Icons.COPY
                    copy_button.update()
                threading.Thread(target=reset_button, daemon=True).start()
            
            copy_button = ft.ElevatedButton(
                "Copy",
                icon=ft.Icons.COPY,
                on_click=copy_to_clipboard,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_100,
                    color=ft.Colors.BLUE_900
                )
            )
            
            content_controls.extend([
                ft.Text("Copy this:", weight=ft.FontWeight.BOLD, size=12),
                ft.Container(
                    content=ft.Text(
                        user_copy_context,
                        selectable=True,
                        size=11,
                        color=ft.Colors.GREY_700,
                        height=80
                    ),
                    bgcolor=ft.Colors.GREY_100,
                    padding=10,
                    border_radius=5,
                    border=ft.border.all(1, ft.Colors.GREY_300)
                ),
                copy_button,
                ft.Divider()
            ])

        if fields and pop_up_type == "form":
            for field in fields:
                field_type = field.get("type", "text")
                field_ref = ft.TextField(
                    label=field["label"],
                    password=field_type == "password",
                    keyboard_type=ft.KeyboardType.EMAIL if field_type == "email" else ft.KeyboardType.TEXT,
                    autofocus=field == fields[0],  # Focus first field
                    height=60

                )
                field["ref"] = field_ref  # Store reference
                content_controls.append(field_ref)

        # Dialog actions
        actions = []
        if pop_up_type == "form" and fields:
            actions.extend([
                ft.ElevatedButton("Login", on_click=handle_submit)
            ])
        else:
            actions.append(
                ft.TextButton("OK", on_click=close_dialog)
            )

        # Create dialog
        dialog = ft.AlertDialog(
            title=ft.Text(title) if title else None,
            content=ft.Column(
                content_controls,
                width=400,
                height=None,
                scroll=ft.ScrollMode.AUTO,  # Enable scrolling
                spacing=10
            ),
            actions=actions,
            modal=True
        )

        # Show dialog
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

        # Poll for completion
        while not self._auth_dialog_complete:
            await asyncio.sleep(0.1)

        result = self._auth_dialog_result

        # Clean up
        self._auth_dialog_result = None
        self._auth_dialog_complete = False

        return result

    def check_for_updates_manual(self):
        """Check for updates manually when user clicks button."""
        
        # Check for updates
        update_info = check_for_desktop_updates()

        if update_info:
            # Update available - show banner
            self.update_info = update_info
            self.show_update_notification()
        else:
            # No update available - show up-to-date message
            self.show_up_to_date_message()

    def show_update_notification(self):
        """Show update notification dialog."""
        if not self.update_info:
            return
        
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        def view_release_and_close(e):
            self.view_release_notes(e)
            close_dialog(e)
            
        def download_and_close(e):
            self.download_update(e)
            close_dialog(e)
        
        # Create update dialog
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.BLUE, size=30),
                ft.Text("Update Available", weight=ft.FontWeight.BOLD)
            ], spacing=10),
            content=ft.Column([
                ft.Text(f"Version {self.update_info['version']} is now available!"),
                ft.Text("Would you like to download the update?", color=ft.Colors.GREY_600)
            ], spacing=10, tight=True),
            actions=[
                ft.TextButton("View Release Notes", on_click=view_release_and_close),
                ft.ElevatedButton("Download Update", on_click=download_and_close),
                ft.TextButton("Later", on_click=close_dialog),
            ],
            modal=True
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def show_up_to_date_message(self):
        """Show message that app is up to date."""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        # Create up-to-date dialog
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=30),
                ft.Text("Up to Date", weight=ft.FontWeight.BOLD)
            ], spacing=10),
            content=ft.Text("You're running the latest version!"),
            actions=[
                ft.ElevatedButton("OK", on_click=close_dialog),
            ],
            modal=True
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def view_release_notes(self, e):
        """Open release notes in browser."""
        if self.update_info:
            import webbrowser
            webbrowser.open(self.update_info['release_url'])

    def download_update(self, e):
        """Handle update download."""
        if not self.update_info or not self.update_info.get('download_url'):
            return
        
        # For now, open download URL in browser
        # In a more advanced implementation, you could download in-app
        import webbrowser
        webbrowser.open(self.update_info['download_url'])
        
        # Show download instructions
        self.show_download_instructions()

    def show_download_instructions(self):
        """Show instructions for installing the downloaded update."""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        instructions = {
            "darwin": "1. Download will start in your browser\n2. Open the downloaded .dmg file\n3. Drag the app to Applications folder\n4. Restart the application",
            "windows": "1. Download will start in your browser\n2. Run the downloaded .exe installer\n3. Follow the installation wizard\n4. Restart the application",
        }
        
        import platform
        current_platform = platform.system().lower()
        instruction_text = instructions.get(current_platform, "Download the update and follow installation instructions.")
        
        dialog = ft.AlertDialog(
            title=ft.Text("Update Installation"),
            content=ft.Column([
                ft.Text(f"Version {self.update_info['version']} Download Instructions:"),
                ft.Text(instruction_text, selectable=True),
                ft.Divider(),
                ft.Text("Release Notes:", weight=ft.FontWeight.BOLD),
                ft.Text(
                    self.update_info.get('release_notes', 'No release notes available.')[:500] + 
                    ('...' if len(self.update_info.get('release_notes', '')) > 500 else ''),
                    selectable=True
                )
            ], width=400, height=300, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("OK", on_click=close_dialog)
            ],
            modal=True
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()



    def check_for_updates_button(self):
        """Check for updates when button is clicked."""
        self.check_for_updates_manual()



def main():
    """Main entry point for the GUI application"""
    os.environ.setdefault("ENTRYPOINT", "GUI")

    def app_main(page: ft.Page):
        TBRDealFinderApp(page)
    
    ft.app(target=app_main)


if __name__ == "__main__":
    main()
