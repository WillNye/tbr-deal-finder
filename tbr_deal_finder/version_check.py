import requests
from packaging import version
import warnings
from tbr_deal_finder import __VERSION__

_PACKAGE_NAME = "tbr-deal-finder"

def check_for_updates():
    """Check if a newer version is available on PyPI."""
    current_version = __VERSION__

    try:
        response = requests.get(
            f"https://pypi.org/pypi/{_PACKAGE_NAME}/json",
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
    latest = check_for_updates()
    if latest:
        warnings.warn(
            f"A new version of {_PACKAGE_NAME} is available ({latest}). "
            f"You have {__VERSION__}. Consider upgrading:\n"
            f"pip install --upgrade {_PACKAGE_NAME}\nOr if you're running using uv:\ngit checkout main && git pull",
            UserWarning,
            stacklevel=2
        )
