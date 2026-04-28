import utils
import requests
import tempfile
import urllib.parse
import config

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

            # Save it to a temporary file with a .jpg extension
            # so utils.py knows how to load it.
            tmp = tempfile.NamedTemporaryFile(
                dir=self.temp_dir,
                suffix=".jpg",
                delete=False
            )
            tmp.write(response.content)
            tmp.close()

            return utils.Path(tmp.name)
