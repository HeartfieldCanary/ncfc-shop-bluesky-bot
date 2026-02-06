import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from atproto import Client, client_utils, models

# CONFIG
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")

PROM_URL = "https://shop.canaries.co.uk/page/discountsandpromotions"
SHOP_HOME = "https://shop.canaries.co.uk/"
# New eye-catching image: Vibrant yellow/green fan celebration
CARD_THUMB_URL = "[attachment_0](attachment)" 

def get_promotions():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔰 Checking NCFC Promotions...")
    try:
        response = requests.get(PROM_URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Pulling the main headline from the promotions page
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

    # 1. Download the new eyecatching thumbnail
    thumb_resp = requests.get(CARD_THUMB_URL)
    thumb_blob = client.upload_blob(thumb_resp.content).blob

    # 2. Build the Link Card (External Embed)
    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="🔰 NCFC Shop Offers",
            description=text,
            uri=SHOP_HOME,
            thumb=thumb_blob,
        )
    )

    # 3. Build the Post Body
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
