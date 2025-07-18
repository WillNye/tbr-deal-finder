import os
from pathlib import Path

QUERY_PATH = Path(__file__).parent.joinpath("queries")

TBR_DEALS_PATH = Path.home() / ".tbr_deal_finder"
os.makedirs(TBR_DEALS_PATH, exist_ok=True)
