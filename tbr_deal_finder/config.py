import configparser
from dataclasses import dataclass
from datetime import datetime

from tbr_deal_finder import TBR_DEALS_PATH

_CONFIG_PATH = TBR_DEALS_PATH.joinpath("config.ini")


@dataclass
class Config:
    story_graph_export_paths: list[str]
    max_price: float = 8.0
    min_discount: int = 35
    run_time: datetime = datetime.now()

    def __post_init__(self):
        if isinstance(self.story_graph_export_paths, str):
            self.story_graph_export_paths = [i.strip() for i in self.story_graph_export_paths.split(",")]
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file or return defaults."""
        if not _CONFIG_PATH.exists():
            raise FileNotFoundError(f"Config file not found at {_CONFIG_PATH}")
        
        parser = configparser.ConfigParser()
        parser.read(_CONFIG_PATH)
        export_paths_str = parser.get('DEFAULT', 'story_graph_export_paths')
        return cls(
            max_price=parser.getfloat('DEFAULT', 'max_price', fallback=8.0),
            min_discount=parser.getint('DEFAULT', 'min_discount', fallback=35),
            story_graph_export_paths=[i.strip() for i in export_paths_str.split(",")]
        )
    
    def save(self):
        """Save configuration to file."""
        parser = configparser.ConfigParser()
        parser['DEFAULT'] = {
            'max_price': str(self.max_price),
            'min_discount': str(self.min_discount),
            'story_graph_export_paths': ", ".join(self.story_graph_export_paths)
        }
        
        with open(_CONFIG_PATH, 'w') as f:
            parser.write(f)
