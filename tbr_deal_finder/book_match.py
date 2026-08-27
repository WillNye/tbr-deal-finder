import logging
import re
from collections import defaultdict
from typing import Iterable, Union

from unidecode import unidecode

from tbr_deal_finder.book import Book, get_normalized_authors, is_matching_authors

logger = logging.getLogger(__name__)

_TITLE_NOISE_RE = re.compile(r'[^a-z0-9 ]')
_TITLE_STOP_WORDS = frozenset({"the", "a", "an", "and"})

_ROLES = (
    "translator", "translated", "narrator", "narrated", "editor", "edited",
    "illustrator", "illustrated", "foreword", "afterword", "introduction",
    "contributor", "adapter", "adaptation", "author", "writer",
)
_ROLE_SUFFIX_RE = re.compile(
    r"\s*[-–—(\[]\s*(?:{})\b.*$".format("|".join(_ROLES)),
    re.IGNORECASE,
)
# A comma-split entry that is nothing but a role, e.g. "Foo, translator".
_ROLE_ONLY_RE = re.compile(r"^\W*(?:{})\W*$".format("|".join(_ROLES)), re.IGNORECASE)
# Imprints/studios credited as authors. Never a person we can match on.
_NON_PERSON_RE = re.compile(
    r"\b(?:publishing|publisher|publishers|press|audio|audiobooks|media|"
    r"productions|production|studio|studios|recorded|books|llc|inc|ltd|gmbh)\b",
    re.IGNORECASE,
)

_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty",
         6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}


def _int_to_words(number: int) -> str:
    """Spell an integer so digit and word forms of a title converge.

    "100 Years of Solitude" and "One Hundred Years of Solitude" both reduce to
    "one hundred years of solitude" once the stop word "and" is dropped.
    """
    if number < 20:
        return _ONES[number]
    if number < 100:
        remainder = number % 10
        return _TENS[number // 10] + ("" if not remainder else f" {_ONES[remainder]}")
    for scale, name in ((1_000_000, "million"), (1_000, "thousand"), (100, "hundred")):
        if number >= scale:
            remainder = number % scale
            head = f"{_int_to_words(number // scale)} {name}"
            return head if not remainder else f"{head} {_int_to_words(remainder)}"
    return str(number)


def canonical_match_title(title: str) -> str:
    """Reduce a title to a key that survives cosmetic disagreement.

    Case, accents, punctuation, leading articles and digit-vs-word numbers are
    all normalized away. The subtitle is dropped at ":" or "(", matching
    :func:`tbr_deal_finder.book.get_normalized_title`.
    """
    title = unidecode(title or "").split(":")[0].split("(")[0].lower()
    title = _TITLE_NOISE_RE.sub(" ", title)

    words = []
    for word in title.split():
        if word.isdigit() and len(word) <= 7:
            words.extend(_int_to_words(int(word)).split())
        else:
            words.append(word)

    return " ".join(word for word in words if word not in _TITLE_STOP_WORDS)


def credited_authors(authors: Union[str, list[str]]) -> list[str]:
    """Normalized author credits with role labels and imprints stripped.

    Role labels ("- translator") are removed but the person is kept; imprints
    ("Crystal Lake Publishing") and bare role words are dropped, since neither
    is a name another source will credit. Falls back to the unfiltered list if
    filtering would leave nothing, so a book credited only to an imprint still
    has something to match on.
    """
    parts = authors.split(",") if isinstance(authors, str) else list(authors or [])

    credits = []
    for part in parts:
        part = _ROLE_SUFFIX_RE.sub("", part).strip()
        if not part or _ROLE_ONLY_RE.match(part) or _NON_PERSON_RE.search(part):
            continue
        credits.append(part)

    return get_normalized_authors(credits or parts)


class BookMatchIndex:
    """Looks books up by title + author with the strict key as the fast path.

    Every match the strict key would have found is still found, so this can only
    ever match more than the previous exact-string comparison, never less.
    """

    def __init__(self, books: Iterable[Book] = (), label: str = "book"):
        self._label = label
        self._exact: dict[str, list[Book]] = defaultdict(list)
        self._by_title: dict[str, list[tuple[list[str], Book]]] = defaultdict(list)
        self._logged: set[tuple[str, str]] = set()

        for book in books:
            self.add(book)

    def add(self, book: Book):
        self._exact[book.full_title_str].append(book)
        self._by_title[canonical_match_title(book.title)].append(
            (credited_authors(book.authors), book)
        )

    def matches(self, book: Book) -> list[Book]:
        """Indexed books that look like the same work as ``book``."""
        results = list(self._exact.get(book.full_title_str, []))
        seen = {id(match) for match in results}

        candidates = self._by_title.get(canonical_match_title(book.title))
        if not candidates:
            return results

        authors = credited_authors(book.authors)
        if not authors:
            return results

        for candidate_authors, candidate in candidates:
            if id(candidate) in seen or not candidate_authors:
                continue
            if not is_matching_authors(authors, candidate_authors):
                continue

            results.append(candidate)
            seen.add(id(candidate))
            self._log_loose_match(book, candidate)

        return results

    def __contains__(self, book: Book) -> bool:
        return bool(self.matches(book))

    def _log_loose_match(self, book: Book, match: Book):
        """Record matches the strict key would have missed, so they're auditable."""
        log_key = (book.full_title_str, match.full_title_str)
        if log_key in self._logged:
            return

        self._logged.add(log_key)
        logger.info(
            'Loose %s match: "%s" by %s matched "%s" by %s [%s]',
            self._label,
            book.title, book.authors, match.title, match.authors, match.retailer,
        )
