import logging

from tbr_deal_finder.book import get_active_deals, Book, is_qualifying_deal
from tbr_deal_finder.gui.pages.base_deals_page import BaseDealsPage

logger = logging.getLogger(__name__)

class AllDealsPage(BaseDealsPage):
    def __init__(self, app):
        super().__init__(app, items_per_page=6)
        
    def get_page_title(self) -> str:
        return "All Active Deals"
    
    def get_empty_state_message(self) -> tuple[str, str]:
        return ("No deals found", "Try adjusting your search or filters")
    
    def load_items(self):
        """Load active deals from database"""
        try:
            self.items = [
                book for book in get_active_deals()
                if is_qualifying_deal(self.app.config, book)
            ]
            self.apply_filters()
        except Exception as e:
            self.items = []
            self.filtered_items = []
            logger.error(f"Error loading deals: {e}")

    def create_item_tile(self, deal: Book):
        return super().create_item_tile(deal)