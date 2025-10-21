import configparser
from dataclasses import dataclass
from datetime import datetime
from typing import Union

from tbr_deal_finder.utils import get_data_dir

_CONFIG_PATH = get_data_dir().joinpath("config.ini")

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


def get_normalized_list(list_val: Union[list, str, None]) -> list:
    if not list_val:
        return []
    elif isinstance(list_val, str):
        list_val = list_val.split(",")

    return [i.strip() for i in list_val if i]


@dataclass
class Config:
    library_export_paths: list[str]
    tracked_retailers: list[str]
    max_price: float = 8.0
    min_discount: int = 30
    run_time: datetime = datetime.now()

    # Both of these are only used if tracking deals on Audible
    is_kindle_unlimited_member: bool = False
    is_audible_plus_member: bool = True
    
    locale: str = "us"  # This will be set as a class attribute below

    def __post_init__(self):
        self.library_export_paths = get_normalized_list(self.library_export_paths)
        self.tracked_retailers = get_normalized_list(self.tracked_retailers)

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

        return cls(
            max_price=parser.getfloat('DEFAULT', 'max_price', fallback=8.0),  
            min_discount=parser.getint('DEFAULT', 'min_discount', fallback=35),
            library_export_paths=get_normalized_list(export_paths_str),
            tracked_retailers=get_normalized_list(tracked_retailers_str),
            is_kindle_unlimited_member=parser.getboolean('DEFAULT', 'is_kindle_unlimited_member', fallback=False),
            is_audible_plus_member=parser.getboolean('DEFAULT', 'is_audible_plus_member', fallback=True)
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

    def save(self):
        """Save configuration to file."""
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {
            'max_price': str(self.max_price),
            'min_discount': str(self.min_discount),
            'locale': type(self).locale,
            'library_export_paths': self.library_export_paths_str,
            'tracked_retailers': self.tracked_retailers_str,
            'is_kindle_unlimited_member': str(self.is_kindle_unlimited_member),
            'is_audible_plus_member': str(self.is_audible_plus_member)
        }
        
        with open(_CONFIG_PATH, 'w') as f:
            parser.write(f)
