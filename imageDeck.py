from utils import *

class ImageDeck:
    def __init__(self):
        image_dir = Path(__file__).parent.resolve() / "images"
        if not image_dir.exists():
            print(f"Error: Folder '{image_dir}' missing!")
            sys.exit()

        self.all_images = [
            f for f in image_dir.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_EXT
        ]

        if not self.all_images:
            print("Error: No images found!")
            sys.exit()
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