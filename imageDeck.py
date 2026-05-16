from dataclasses import dataclass
import requests
import urllib.parse
import redgifs
from redgifs.enums import MediaType, Order
from redgifs.errors import HTTPException
from redgifs.utils import _read_tags_json

import config
import utils


def _filename_from_url(url, fallback_suffix=".jpg"):
    """Extract a sanitized filename from a URL, falling back to a random name."""
    try:
        raw = urllib.parse.urlparse(url).path
        name = utils.Path(raw).name
        # Strip query strings that sneak into the path segment
        name = name.split("?")[0]
        if name and "." in name:
            return name
    except Exception:
        pass
    import uuid
    return f"{uuid.uuid4().hex}{fallback_suffix}"

class LocalImageDeck:
    def __init__(self, custom_path=None):
        if config.CUSTOM_PATH:
            image_dir = utils.Path(config.CUSTOM_PATH).resolve()
        else:
            image_dir = utils.Path(__file__).parent.resolve() / "images"

        self.all_images = [
            f for f in image_dir.iterdir()
            if f.is_file() and f.suffix.lower() in config.VALID_EXT
        ]

        if not self.all_images:
             raise ValueError("No images found!")
        self.deck = []
        self.shuffle_deck()
        
    def shuffle_deck(self):
        """Refill and shuffle the deck."""
        self.deck = self.all_images.copy()
        utils.random.shuffle(self.deck)

    def next_image(self):
        """Get next image from deck."""
        if not self.deck:
            self.shuffle_deck()
        return self.deck.pop()
    
class PexelsImageDeck:
    def __init__(self, query=None, per_page = 15):
        self.query = query
        self.per_page = per_page
        self.session = requests.Session()
        self.session.headers.update({"Authorization": config.PEXELS_API_KEY})
        self.deck_urls = []

        self.page = utils.random.randint(1, 100)

        game_dir = utils.Path(__file__).parent.resolve()
        self.temp_dir = game_dir / "temp" / "temp_pexels"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.shuffle_deck()
    
    def shuffle_deck(self):
        """Fetch a new page of images from Pexels and shuffle them."""
        for _ in range(2):
            if self.query:
                url = f"https://api.pexels.com/v1/search?query={self.query}&per_page={self.per_page}&page={self.page}&size=large"
            else:
                url = f"https://api.pexels.com/v1/curated?per_page={self.per_page}&page={self.page}"

            try:
                response = self.session.get(url, timeout=config.NETWORK_TIMEOUT)
            except requests.RequestException as exc:
                print(f"Error fetching from Pexels: {exc}")
                self.deck_urls = []
                return

            if response.status_code != 200:
                print(f"Error fetching from Pexels: {response.status_code}")
                self.deck_urls = []
                return

            data = response.json()
            photos = data.get('photos', [])

            # If your random page was too high reset to page 1 and try again to prevent crashing.
            if not photos and self.page > 1:
                print(f"Page {self.page} was empty. Resetting to page 1.")
                self.page = 1
                continue

            self.deck_urls = [photo['src']['original'] for photo in photos]
            utils.random.shuffle(self.deck_urls)
            self.page += 1
            return

        self.deck_urls = []

    def next_image(self):
        """Get next URL from deck, download it, and return its local Path."""
        while True:
            if not self.deck_urls:
                self.shuffle_deck()
            if not self.deck_urls:
                return None

            img_url = self.deck_urls.pop()
            try:
                response = self.session.get(img_url, timeout=config.DOWNLOAD_TIMEOUT)
            except requests.RequestException as exc:
                print(f"Failed to download image: {exc}")
                continue

            if response.status_code != 200:
                print(f"Failed to download image. Status: {response.status_code}")
                continue

            # Save with the original filename so saves are human-readable
            filename = _filename_from_url(img_url, fallback_suffix=".jpg")
            dest = self.temp_dir / filename
            dest.write_bytes(response.content)
            return dest

@dataclass(frozen=True)
class DeckSpec:
    key: str
    label: str
    description: str
    factory: type
    supports_search: bool


DECK_SPECS = (
    DeckSpec(
        "local",
        "Local Images",
        "Use files from your local images folder.",
        LocalImageDeck,
        False,
    ),
    DeckSpec(
        "pexels",
        "Pexels",
        "Pull curated or searched photos from Pexels.",
        PexelsImageDeck,
        True,
    ),
)

DECK_SPECS_BY_KEY = {spec.key: spec for spec in DECK_SPECS}


def get_deck_specs():
    return DECK_SPECS


def get_deck_spec_for_instance(deck):
    if deck is None:
        return None

    for spec in DECK_SPECS:
        if isinstance(deck, spec.factory):
            return spec

    return None


def create_deck(deck_key, query=None):
    spec = DECK_SPECS_BY_KEY[deck_key]
    if query:
        return spec.factory(query=query)
    return spec.factory()
