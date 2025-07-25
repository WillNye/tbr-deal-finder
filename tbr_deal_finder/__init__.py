import os
from pathlib import Path

__VERSION__ = "0.1.0"

QUERY_PATH = Path(__file__).parent.joinpath("queries")

TBR_DEALS_PATH = Path.home() / ".tbr_deal_finder"
os.makedirs(TBR_DEALS_PATH, exist_ok=True)
