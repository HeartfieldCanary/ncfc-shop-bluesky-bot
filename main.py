import os
import requests
from bs4 import BeautifulSoup
from atproto import Client, client_utils, models
from io import BytesIO
from PIL import Image

# CONFIG
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")

PROM_URL = "https://shop.canaries.co.uk/page/discountsandpromotions"
SHOP_HOME = "https://shop.canaries.co.uk/"
IMAGE_PATH = "ncfcshop.png" 

def get_promotions():
    # Adding a User-Agent makes the script look like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(PROM_URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This is the exact container for the shop's promo text
        page_body = soup.find('div', class_='page-body')
        if not page_body:
            return "Check out the latest offers at the Norwich City Shop!"

        promos = []
        # Look for headers and list items which contain the '40% Off' and 'Free Printing' text
        for element in page_body.find_all(['h2', 'h3', 'li', 'strong']):
            text = element.get_text(strip=True)
            # Filter for keywords to grab specific deals
            if any(word in text.lower() for word in ["off", "%", "free", "sale", "printing"]):
                if text not in promos and len(text) > 5:
                    promos.append(text)
        
        if promos:
            # Taking the top 3 deals to keep the post concise
            return "\n".join([f"• {p}" for p in promos[:3]])
        
        return "New promotions are live! Visit the shop for details."

    except Exception as e:
        print(f"Error scraping: {e}")
        return "Check out the latest offers at the Norwich City Shop!"

def post_to_bluesky(promo_text):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

    # Process Thumbnail Image
    if os.path.exists(IMAGE_PATH):
        with Image.open(IMAGE_PATH) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            img_data = buffer.getvalue()
        thumb_blob = client.upload_blob(img_data).blob
    else:
        print("Image not found - skipping thumbnail.")
        thumb_blob = None

    # Use TextBuilder to create 'Facets' (clickable links/hashtags)
    tb = client_utils.TextBuilder()
    tb.text("🔰 Norwich City Shop Promotions\n\n")
    tb.text(f"{promo_text}\n\n")
    tb.tag("#NCFC", "NCFC") # This makes the hashtag blue and clickable

    # Create the Link Card
    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="NCFC Official Shop Offers",
            description="View all current promotions and kits.",
            uri=SHOP_HOME,
            thumb=thumb_blob,
        )
    )

    client.send_post(text=tb, embed=embed_external)
    print("Post sent successfully!")

if __name__ == "__main__":
    promo_data = get_promotions()
    post_to_bluesky(promo_data)
