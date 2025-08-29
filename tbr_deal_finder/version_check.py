import requests
from packaging import version
import warnings
from ._version import __version__


def check_for_updates(package_name):
    """Check if a newer version is available on PyPI."""
    current_version = __version__

    try:
        response = requests.get(
            f"https://pypi.org/pypi/{package_name}/json",
            timeout=2  # Don't hang if PyPI is slow
        )
        response.raise_for_status()

        latest_version = response.json()["info"]["version"]

        if version.parse(latest_version) > version.parse(current_version):
            return latest_version
        return None

    except Exception:
        # Silently fail - don't break user's code over version check
        return None


def notify_if_outdated():
    """Show a warning if package is outdated."""
    package_name = "tbr-deal-finder"
    latest = check_for_updates(package_name)
    if latest:
        warnings.warn(
            f"A new version of {package_name} is available ({latest}). "
            f"You have {__version__}. Consider upgrading: "
            f"pip install --upgrade {package_name}",
            UserWarning,
            stacklevel=2
        )
