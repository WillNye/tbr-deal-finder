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
    story_graph_export_paths: list[str]
    max_price: float = 8.0
    min_discount: int = 35
    run_time: datetime = datetime.now()
    
    locale: str = "us"  # This will be set as a class attribute below

    def __post_init__(self):
        if isinstance(self.story_graph_export_paths, str):
            self.set_story_graph_export_paths(
                self.story_graph_export_paths.split(",")
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
        export_paths_str = parser.get('DEFAULT', 'story_graph_export_paths')
        locale = parser.get('DEFAULT', 'locale', fallback="us")
        cls.set_locale(locale)
        return cls(
            max_price=parser.getfloat('DEFAULT', 'max_price', fallback=8.0),  
            min_discount=parser.getint('DEFAULT', 'min_discount', fallback=35),
            story_graph_export_paths=[i.strip() for i in export_paths_str.split(",")]
        )

    @property
    def story_graph_export_paths_str(self) -> str:
        return ", ".join(self.story_graph_export_paths)

    def set_story_graph_export_paths(self, story_graph_export_paths: Union[str, list[str]]):
        if isinstance(story_graph_export_paths, str):
            self.story_graph_export_paths = [i.strip() for i in story_graph_export_paths.split(",")]
        else:
            self.story_graph_export_paths = story_graph_export_paths

    def save(self):
        """Save configuration to file."""
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {
            'max_price': str(self.max_price),
            'min_discount': str(self.min_discount),
            'locale': type(self).locale,
            'story_graph_export_paths': self.story_graph_export_paths_str
        }
        
        with open(_CONFIG_PATH, 'w') as f:
            parser.write(f)
