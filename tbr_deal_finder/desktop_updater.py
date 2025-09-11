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
                download_url = release_data["html_url"]
                if self.platform == "darwin":
                    for asset in release_data["assets"]:
                        if asset["browser_download_url"].endswith(".dmg"):
                            download_url = asset["browser_download_url"]

                return {
                    "version": latest_version,
                    "download_url": download_url,
                    "release_notes": release_data.get("body", ""),
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to check updates for {self.github_repo}: {e}")
            return None


# Global instance
desktop_updater = DesktopUpdater()


def check_for_desktop_updates() -> Optional[Dict[str, Any]]:
    """Convenience function to check for updates."""
    return desktop_updater.check_for_updates()
