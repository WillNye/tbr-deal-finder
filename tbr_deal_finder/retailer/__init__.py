from tbr_deal_finder.retailer.audible import Audible
from tbr_deal_finder.retailer.chirp import Chirp
from tbr_deal_finder.retailer.kindle import Kindle
from tbr_deal_finder.retailer.kobo import KoboEbook, KoboAudiobook
from tbr_deal_finder.retailer.librofm import LibroFM

WHISPERSYNC_HINT = (
    "Tip: also track Kindle to get Whispersync pricing on Audible, Kindle Unlimited member or not. "
    "With the Kindle ebook (owned, borrowed, or bought on sale) the Audible narration is often "
    "far cheaper, sometimes under half the cost of a credit even after buying the ebook."
)

RETAILER_MAP = {
    "Audible": Audible,
    "Chirp": Chirp,
    "Libro.FM": LibroFM,
    "Kindle": Kindle,
    "Kobo E-Book": KoboEbook,
    "Kobo Audiobook": KoboAudiobook,
}
