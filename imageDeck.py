from utils import *
import requests
import tempfile
import urllib.parse

class LocalImageDeck:
    def __init__(self):
        image_dir = Path(__file__).parent.resolve() / "images"
        self.all_images = [
            f for f in image_dir.iterdir()
            if f.is_file() and f.suffix.lower() in VALID_EXT
        ]

        if not self.all_images:
             raise ValueError("No images found!")
        self.deck = []
        self.shuffle_deck()
        
    def shuffle_deck(self):
        """Refill and shuffle the deck."""
        self.deck = self.all_images.copy()
        random.shuffle(self.deck)

    def next_image(self):
        """Get next image from deck."""
        if not self.deck:
            self.shuffle_deck()
        return self.deck.pop()
    
class PexelsImageDeck:
    def __init__(self, query=None, per_page = 15):
        self.query = query
        self.per_page = per_page
        self.headers = {"Authorization": PEXELS_API_KEY}
        self.deck_urls = []
        self.page = 1

        game_dir = Path(__file__).parent.resolve()
        self.temp_dir = game_dir / "temp" / "temp_pexels"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.shuffle_deck()
    
    def shuffle_deck(self):
        """Fetch a new page of images from Pexels and shuffle them."""
        
        if self.query:
            url = f"https://api.pexels.com/v1/search?query={self.query}&per_page={self.per_page}&page={self.page}"
        else:
            url = f"https://api.pexels.com/v1/curated?per_page={self.per_page}&page={self.page}"
        
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            photos = data.get('photos', [])
            
            # full-resolution image
            self.deck_urls = [photo['src']['original'] for photo in photos]
            random.shuffle(self.deck_urls)
            self.page += 1  # Increment so the next shuffle gets fresh images
        else:
            print(f"Error fetching from Pexels: {response.status_code}")
            self.deck_urls = []

        if not self.deck_urls:
            raise ValueError("No images found from Pexels! Check your API key or query.")

    def next_image(self):
        """Get next URL from deck, download it, and return its local Path."""
        if not self.deck_urls:
            self.shuffle_deck()
        
        img_url = self.deck_urls.pop()
        response = requests.get(img_url)
        if response.status_code == 200:
            # Save it to a temporary file with a .jpg extension
            # so utils.py knows how to load it.
            tmp = tempfile.NamedTemporaryFile(
                dir=self.temp_dir,
                suffix=".jpg",
                delete=False
            )
            tmp.write(response.content)
            tmp.close()
            
            return Path(tmp.name)
        else:
            print(f"Failed to download image. Status: {response.status_code}")
            # If download fails, try the next one recursively
            return self.next_image()