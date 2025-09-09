from pathlib import Path

import flet as ft

from tbr_deal_finder.config import Config
from tbr_deal_finder.retailer import RETAILER_MAP
from tbr_deal_finder.tracked_books import reprocess_incomplete_tbr_books, clear_unknown_books


class SettingsPage:
    def __init__(self, app):
        self.app = app
        self.config = None
        self.library_paths = []
        self.tracked_retailers = []
        self.max_price = 8.0
        self.min_discount = 30
        self.locale = "us"
        
        # Create file picker once and add to page overlay
        self.file_picker = ft.FilePicker(on_result=self.on_file_picker_result)
        
        self.load_current_config()

    def load_current_config(self):
        """Load current configuration or set defaults"""
        try:
            self.config = Config.load()
            self.library_paths = self.config.library_export_paths.copy()
            self.tracked_retailers = self.config.tracked_retailers.copy()
            self.max_price = self.config.max_price
            self.min_discount = self.config.min_discount
            self.locale = self.config.locale
        except FileNotFoundError:
            self.library_paths = []
            self.tracked_retailers = list(RETAILER_MAP.keys())

    def build(self):
        """Build the settings page content"""
        
        # Add file picker to page overlay if not already added
        if self.file_picker not in self.app.page.overlay:
            self.app.page.overlay.append(self.file_picker)
            self.app.page.update()  # Important: update page after adding to overlay
        
        # Library Export Paths Section
        self.library_paths_list = ft.ListView(
            height=150,
            spacing=5
        )
        self.update_library_paths_list()
        
        library_section = ft.Container(
            content=ft.Column([
                ft.Text("Library Export Paths", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("Add your StoryGraph or Goodreads export files", color=ft.Colors.GREY_600),
                self.library_paths_list,
                ft.Row([
                    ft.ElevatedButton(
                        "Browse Files",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=self.add_library_path
                    ),
                    ft.ElevatedButton(
                        "Enter Path Manually",
                        icon=ft.Icons.EDIT,
                        on_click=lambda e: self.show_text_input_dialog()
                    ),
                    ft.OutlinedButton(
                        "Remove Selected",
                        icon=ft.Icons.REMOVE,
                        on_click=self.remove_library_path
                    )
                ], wrap=True)
            ], spacing=10),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

        # Tracked Retailers Section
        retailer_checkboxes = []
        for retailer in RETAILER_MAP.keys():
            checkbox = ft.Checkbox(
                label=retailer,
                value=retailer in self.tracked_retailers,
                on_change=lambda e, r=retailer: self.toggle_retailer(r, e.control.value)
            )
            retailer_checkboxes.append(checkbox)

        retailers_section = ft.Container(
            content=ft.Column([
                ft.Text("Tracked Retailers", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("Select retailers to check for deals", color=ft.Colors.GREY_600),
                ft.Column(retailer_checkboxes, spacing=5)
            ], spacing=10),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

        # Locale Selection
        locale_options = {
            "US and all other countries not listed": "us",
            "Canada": "ca",
            "UK and Ireland": "uk",
            "Australia and New Zealand": "au",
            "France, Belgium, Switzerland": "fr",
            "Germany, Austria, Switzerland": "de",
            "Japan": "jp",
            "Italy": "it",
            "India": "in",
            "Spain": "es",
            "Brazil": "br"
        }
        
        current_locale_name = [k for k, v in locale_options.items() if v == self.locale][0]
        
        self.locale_dropdown = ft.Dropdown(
            value=current_locale_name,
            options=[ft.dropdown.Option(k) for k in locale_options.keys()],
            on_change=lambda e: setattr(self, 'locale', locale_options[e.control.value])
        )

        # Price and Discount Settings
        self.max_price_field = ft.TextField(
            label="Maximum Price",
            value=str(self.max_price),
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self.update_max_price
        )
        
        self.min_discount_field = ft.TextField(
            label="Minimum Discount %",
            value=str(self.min_discount),
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self.update_min_discount
        )

        price_section = ft.Container(
            content=ft.Column([
                ft.Text("Deal Criteria", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.max_price_field,
                    self.min_discount_field
                ], spacing=20),
                ft.Text("Locale", size=16, weight=ft.FontWeight.BOLD),
                self.locale_dropdown
            ], spacing=10),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8
        )

        # Save and Cancel buttons
        button_row = ft.Row([
            ft.ElevatedButton(
                "Save Configuration",
                icon=ft.Icons.SAVE,
                on_click=self.save_config
            ),
            ft.OutlinedButton(
                "Cancel",
                on_click=self.cancel_changes
            )
        ], spacing=10)
        
        # Update check section
        update_section = ft.Container(
            content=ft.Column([
                ft.Text("Application Updates", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("Check for the latest version", color=ft.Colors.GREY_600),
                ft.ElevatedButton(
                    "Check for Updates",
                    icon=ft.Icons.SYSTEM_UPDATE,
                    on_click=lambda e: self.app.check_for_updates_button(),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600),
                )
            ], spacing=10),
            padding=20,
        )

        # Main settings content
        main_content = ft.ListView([
            ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
            library_section,
            retailers_section,
            price_section,
            button_row
        ], spacing=20, padding=ft.padding.all(20), expand=True)
        
        # Create layout with main content on left and update section on right
        return ft.Row([
            main_content,
            ft.Container(
                content=update_section,
                width=300,
                alignment=ft.alignment.top_left
            )
        ], spacing=20, expand=True)

    def update_library_paths_list(self):
        """Update the library paths list view"""
        self.library_paths_list.controls.clear()
        for i, path in enumerate(self.library_paths):
            item = ft.ListTile(
                title=ft.Text(path),
                trailing=ft.Checkbox(value=False),
                dense=True
            )
            self.library_paths_list.controls.append(item)
        self.app.page.update()

    def add_library_path(self, e):
        """Add a new library export path"""
        def on_result(e: ft.FilePickerResultEvent):
            if e.files and len(e.files) > 0:
                new_path = e.files[0].path
                if new_path not in self.library_paths:
                    self.library_paths.append(new_path)
                    self.update_library_paths_list()

        # Create a file picker for this operation
        file_picker = ft.FilePicker(on_result=on_result)
        
        # Add to overlay
        self.app.page.overlay.append(file_picker)
        self.app.page.update()

        # Open the file picker
        file_picker.pick_files(
            dialog_title="Select Library Export File",
            file_type=ft.FilePickerFileType.CUSTOM,
            initial_directory=str(Path.home()),
            allowed_extensions=["csv"]
        )

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Handle file picker result (legacy method - not used with new implementation)"""
        if e.files:
            for f in e.files:
                new_path = f.path
                if new_path not in self.library_paths:
                    self.library_paths.append(new_path)
                    self.update_library_paths_list()

    def remove_library_path(self, e):
        """Remove selected library paths"""
        to_remove = []
        for i, control in enumerate(self.library_paths_list.controls):
            if control.trailing.value:  # If checkbox is checked
                to_remove.append(i)
        
        # Remove in reverse order to maintain indices
        for i in reversed(to_remove):
            self.library_paths.pop(i)
        
        self.update_library_paths_list()

    def toggle_retailer(self, retailer: str, is_checked: bool):
        """Toggle retailer tracking"""
        if is_checked and retailer not in self.tracked_retailers:
            self.tracked_retailers.append(retailer)
        elif not is_checked and retailer in self.tracked_retailers:
            self.tracked_retailers.remove(retailer)

    def update_max_price(self, e):
        """Update max price value"""
        try:
            self.max_price = float(e.control.value)
        except ValueError:
            pass

    def update_min_discount(self, e):
        """Update min discount value"""
        try:
            self.min_discount = int(e.control.value)
        except ValueError:
            pass

    def save_config(self, e):
        """Save the configuration"""
        if not self.tracked_retailers:
            self.show_error("You must track at least one retailer.")
            return

        try:
            if self.config:
                # Update existing config
                self.config.library_export_paths = self.library_paths
                self.config.tracked_retailers = self.tracked_retailers
                self.config.max_price = self.max_price
                self.config.min_discount = self.min_discount
                self.config.set_locale(self.locale)
            else:
                # Create new config
                self.config = Config(
                    library_export_paths=self.library_paths,
                    tracked_retailers=self.tracked_retailers,
                    max_price=self.max_price,
                    min_discount=self.min_discount
                )
                self.config.set_locale(self.locale)

            self.config.save()
            
            # Reprocess books if retailers changed
            reprocess_incomplete_tbr_books(self.config)
            clear_unknown_books()
            
            self.show_success("Configuration saved successfully!")
            self.app.enable_navigation()
            self.app.config_updated(self.config)
            
        except Exception as ex:
            self.show_error(f"Error saving configuration: {str(ex)}")

    def cancel_changes(self, e):
        """Cancel changes and return to main view"""
        self.load_current_config()
        if self.app.config:
            self.app.current_page = "all_deals"
            self.app.nav_rail.selected_index = 0
        else:
            self.app.current_page = "all_deals"
        self.app.update_content()

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

    def show_text_input_dialog(self):
        """Fallback: Show text input dialog for manual path entry"""
        self.path_input = ft.TextField(
            label="Enter full path to CSV file",
            hint_text="/path/to/your/export.csv",
            expand=True
        )
        
        def add_manual_path(e):
            path = self.path_input.value.strip()
            if path and path not in self.library_paths:
                import os
                if os.path.exists(path) and path.endswith('.csv'):
                    self.library_paths.append(path)
                    self.update_library_paths_list()
                    self.close_dialog(path_dialog)
                else:
                    self.show_error("File does not exist or is not a CSV file")
            else:
                self.show_error("Please enter a valid path")
        
        path_dialog = ft.AlertDialog(
            title=ft.Text("Enter File Path"),
            content=ft.Column([
                ft.Text("File picker not available. Please enter the full path to your library export CSV file:"),
                self.path_input
            ], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(path_dialog)),
                ft.ElevatedButton("Add Path", on_click=add_manual_path)
            ]
        )
        
        self.app.page.overlay.append(path_dialog)
        path_dialog.open = True
        self.app.page.update()

    def close_dialog(self, dialog):
        """Close dialog"""
        dialog.open = False
        self.app.page.update()
