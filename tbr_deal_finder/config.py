import configparser
from dataclasses import dataclass
from datetime import datetime
from typing import Union

from tbr_deal_finder import TBR_DEALS_PATH

_CONFIG_PATH = TBR_DEALS_PATH.joinpath("config.ini")

_LOCALE_CURRENCY_MAP = {
    "us": "$",
    "ca": "$",
    "au": "$",
    "uk": "£",
    "fr": "€",
    "de": "€",
    "es": "€",
    "it": "€",
    "jp": "¥",
    "in": "₹",
    "br": "R$",
}

@dataclass
class Config:
    library_export_paths: list[str]
    tracked_retailers: list[str]
    max_price: float = 8.0
    min_discount: int = 35
    run_time: datetime = datetime.now()
    
    locale: str = "us"  # This will be set as a class attribute below

    def __post_init__(self):
        if isinstance(self.library_export_paths, str):
            self.set_library_export_paths(
                self.library_export_paths.split(",")
            )

        if isinstance(self.tracked_retailers, str):
            self.set_tracked_retailers(
                self.tracked_retailers.split(",")
            )

    @classmethod
    def currency_symbol(cls) -> str:
        return _LOCALE_CURRENCY_MAP.get(cls.locale, "$")

    @classmethod
    def set_locale(cls, code: str):
        cls.locale = code

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file or return defaults."""
        if not _CONFIG_PATH.exists():
            raise FileNotFoundError(f"Config file not found at {_CONFIG_PATH}")
        
        parser = configparser.ConfigParser()
        parser.read(_CONFIG_PATH)
        export_paths_str = parser.get('DEFAULT', 'library_export_paths')
        tracked_retailers_str = parser.get('DEFAULT', 'tracked_retailers')
        locale = parser.get('DEFAULT', 'locale', fallback="us")
        cls.set_locale(locale)

        if export_paths_str:
            library_export_paths = [i.strip() for i in export_paths_str.split(",")]
        else:
            library_export_paths = []

        return cls(
            max_price=parser.getfloat('DEFAULT', 'max_price', fallback=8.0),  
            min_discount=parser.getint('DEFAULT', 'min_discount', fallback=35),
            library_export_paths=library_export_paths,
            tracked_retailers=[i.strip() for i in tracked_retailers_str.split(",")]
        )

    @property
    def library_export_paths_str(self) -> str:
        return ", ".join(self.library_export_paths)

    @property
    def tracked_retailers_str(self) -> str:
        return ", ".join(self.tracked_retailers)

    def is_tracking_format(self, book_format) -> bool:
        from tbr_deal_finder.retailer import RETAILER_MAP

        for retailer_str in self.tracked_retailers:
            retailer = RETAILER_MAP[retailer_str]()
            if retailer.format == book_format:
                return True

        return False

    def set_library_export_paths(self, library_export_paths: Union[str, list[str]]):
        if not library_export_paths:
            self.library_export_paths = []
        elif isinstance(library_export_paths, str):
            self.library_export_paths = [i.strip() for i in library_export_paths.split(",")]
        else:
            self.library_export_paths = library_export_paths

    def set_tracked_retailers(self, tracked_retailers: Union[str, list[str]]):
        if isinstance(tracked_retailers, str):
            self.tracked_retailers = [i.strip() for i in tracked_retailers.split(",")]
        else:
            self.tracked_retailers = tracked_retailers

    def save(self):
        """Save configuration to file."""
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {
            'max_price': str(self.max_price),
            'min_discount': str(self.min_discount),
            'locale': type(self).locale,
            'library_export_paths': self.library_export_paths_str,
            'tracked_retailers': self.tracked_retailers_str
        }
        
        with open(_CONFIG_PATH, 'w') as f:
            parser.write(f)
