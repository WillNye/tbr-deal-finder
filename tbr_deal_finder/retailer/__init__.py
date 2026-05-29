from tbr_deal_finder.retailer.audible import Audible
from tbr_deal_finder.retailer.chirp import Chirp
from tbr_deal_finder.retailer.kindle import Kindle
from tbr_deal_finder.retailer.kobo import KoboEbook, KoboAudiobook
from tbr_deal_finder.retailer.librofm import LibroFM

RETAILER_MAP = {
    "Audible": Audible,
    "Chirp": Chirp,
    "Libro.FM": LibroFM,
    "Kindle": Kindle,
    "Kobo E-Book": KoboEbook,
    "Kobo Audiobook": KoboAudiobook,
}
