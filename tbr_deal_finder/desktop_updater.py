"""
Desktop application update checker and handler.
For packaged desktop applications (.dmg/.exe).
"""
import json
import logging
import os
import platform
import subprocess
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from packaging import version

from tbr_deal_finder import __VERSION__

logger = logging.getLogger(__name__)

class DesktopUpdater:
    """Handle updates for packaged desktop applications."""
    
    def __init__(self, github_repo: str = "WillNye/tbr-deal-finder"):
        self.github_repo = github_repo
        self.current_version = __VERSION__
        self.platform = platform.system().lower()
        
    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """
        Check GitHub releases for newer versions.
        Returns dict with update info or None if no update available.
        """
        try:
            # Check GitHub releases API
            response = requests.get(
                f"https://api.github.com/repos/{self.github_repo}/releases/latest",
                timeout=5
            )
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data["tag_name"].lstrip("v")
            if version.parse(latest_version) > version.parse(self.current_version):
                release_url = release_data["html_url"]
                return {
                    "version": latest_version,
                    "download_url": release_url,
                    "release_notes": release_data.get("body", ""),
                    "release_url": release_url
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to check updates for {self.github_repo}: {e}")
            return None
    
    def download_update(self, download_url: str, progress_callback=None) -> Optional[Path]:
        """
        Download the update file.
        Returns path to downloaded file or None if failed.
        """
        try:
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determine file extension
            filename = download_url.split("/")[-1]
            temp_file = Path(tempfile.gettempdir()) / filename
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            return temp_file
            
        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            return None
    
    def install_update(self, update_file: Path) -> bool:
        """
        Install the downloaded update.
        Platform-specific installation logic.
        """
        if self.platform == "darwin":
            return self._install_macos_update(update_file)
        elif self.platform == "windows":
            return self._install_windows_update(update_file)
        elif self.platform == "linux":
            return self._install_linux_update(update_file)
        else:
            return False
    
    def _install_macos_update(self, dmg_file: Path) -> bool:
        """Install .dmg update on macOS."""
        try:
            # Open the DMG file - user will need to drag to Applications
            subprocess.run(["open", str(dmg_file)], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _install_windows_update(self, exe_file: Path) -> bool:
        """Install .exe update on Windows."""
        try:
            # Run the installer
            subprocess.run([str(exe_file)], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _install_linux_update(self, appimage_file: Path) -> bool:
        """Install AppImage update on Linux."""
        try:
            # Make executable and offer to replace current installation
            os.chmod(appimage_file, 0o755)
            
            # For AppImage, we'd typically replace the current file
            # This is more complex and might require user permission
            return True
        except Exception:
            return False
    
    def open_download_page(self, release_url: str):
        """Open the GitHub release page in browser."""
        webbrowser.open(release_url)


# Global instance
desktop_updater = DesktopUpdater()


def check_for_desktop_updates() -> Optional[Dict[str, Any]]:
    """Convenience function to check for updates."""
    return desktop_updater.check_for_updates()
