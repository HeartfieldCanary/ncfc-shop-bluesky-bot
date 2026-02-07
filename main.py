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
        
        page_body = soup.select_one(".page-body")
        if not page_body:
            return "Check out the latest offers at the Norwich City Shop!"

        promos = []
        # Target headers, list items, and bold text specifically
        for element in page_body.find_all(['h2', 'h3', 'strong', 'li', 'p']):
            text = element.get_text(strip=True)
            # Filter for keywords to ensure we get actual deals
            if any(word in text for word in ["Off", "%", "Free", "Sale", "Code", "Discount"]):
                # Clean up nested text and avoid duplicates
                if text not in promos and len(text) > 5:
                    promos.append(text)
        
        if promos:
            # Format with bullet points, capped at 4 to stay under character limits
            return "\n".join([f"• {p}" for p in promos[:4]])
        
        return "New promotions are live! Visit the shop for details."

    except Exception as e:
        print(f"❌ Scrape Error: {e}")
        return "Check out the latest offers at the Norwich City Shop!"

def post_to_bluesky(promo_text):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

    # Image Processing (Compression for Bluesky limits)
    if os.path.exists(IMAGE_PATH):
        with Image.open(IMAGE_PATH) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=75, optimize=True)
            img_data = buffer.getvalue()
        thumb_blob = client.upload_blob(img_data).blob
    else:
        print(f"❌ Error: {IMAGE_PATH} not found.")
        return

    # Build the post body
    tb = client_utils.TextBuilder()
    tb.text("🔰 Norwich City Shop Promotions\n\n")
    tb.text(promo_text)
    tb.text("\n\n#NCFC #OTBC #Canaries")

    # Build the Link Card
    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="NCFC Official Shop Offers",
            description="View the latest discounts and kits.",
            uri=SHOP_HOME,
            thumb=thumb_blob,
        )
    )

    client.send_post(text=tb, embed=embed_external)
    print("🎉 Post successful!")

def main():
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        print("❌ Secrets missing.")
        return

    promo_info = get_promotions()
    post_to_bluesky(promo_info)

if __name__ == "__main__":
    main()
