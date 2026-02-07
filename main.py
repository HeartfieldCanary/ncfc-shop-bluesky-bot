import os
import requests
from datetime import datetime
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔰 Checking NCFC Promotions...")
    try:
        response = requests.get(PROM_URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        promo_headings = soup.select(".page-body h2, .page-body h3, .page-body p strong")
        
        if promo_headings:
            headline = promo_headings[0].get_text(strip=True)
            return headline
        return "Check out the latest offers at the Norwich City Shop!"
    except Exception as e:
        print(f"❌ Scrape Error: {e}")
        return "New promotions available at the NCFC Shop!"

def post_to_bluesky(text):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

    if os.path.exists(IMAGE_PATH):
        with Image.open(IMAGE_PATH) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=70, optimize=True)
            img_data = buffer.getvalue()
        thumb_blob = client.upload_blob(img_data).blob
    else:
        print(f"❌ Error: {IMAGE_PATH} not found.")
        return

    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="🔰 NCFC Shop Offers",
            description=text,
            uri=SHOP_HOME,
            thumb=thumb_blob,
        )
    )

    tb = client_utils.TextBuilder()
    tb.text(f"🔰 NCFC SHOP UPDATE\n\n{text}\n\n#NCFC")

    client.send_post(text=tb, embed=embed_external)
    print("🎉 Post successful!")

def main():
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        print("❌ Secrets missing.")
        return

    headline = get_promotions()
    post_to_bluesky(headline)

if __name__ == "__main__":

  main()
