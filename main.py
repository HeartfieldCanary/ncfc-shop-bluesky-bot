import os
import json
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from atproto import Client, client_utils

# CONFIG
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
FORCE_POST = os.environ.get("FORCE_POST", "false").lower() == "true"

HOME_URL = "https://shop.canaries.co.uk/"
SEEN_FILE = "seen_banners.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except:
            return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def scrape_banners(driver):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🏠 Scraping NCFC Shop...")
    driver.get(HOME_URL)
    banners = []
    
    try:
        # Give the page plenty of time to load the Javascript carousel
        time.sleep(8) 

        # We are looking for images inside the main homepage promo areas
        # NCFC shop usually uses specific containers for their big ads
        targets = [
            ".home-carousel img", 
            ".hero-slider img", 
            ".promo-banner img",
            ".flexslider img",
            "main img" # Fallback to any image in the main body
        ]
        
        found_elements = driver.find_elements(By.CSS_SELECTOR, ", ".join(targets))
        print(f"🔎 Found {len(found_elements)} potential images. Filtering...")

        for img_el in found_elements:
            try:
                img_url = img_el.get_attribute("src")
                alt_text = img_el.get_attribute("alt") or "Norwich City FC Promotion"
                
                # Try to find a link nearby
                parent = img_el.find_element(By.XPATH, "./..")
                link = parent.get_attribute("href") or HOME_URL

                # FILTER: We want large images, not small icons or payment logos
                width = img_el.size.get('width', 0)
                height = img_el.size.get('height', 0)

                if img_url and (width > 400 or "banner" in img_url.lower()):
                    if img_url not in [b['img'] for b in banners]:
                        banners.append({
                            "id": img_url, 
                            "img": img_url,
                            "link": link,
                            "text": alt_text
                        })
            except:
                continue
        
        return banners
    except Exception as e:
        print(f"❌ Scrape Error: {e}")
        return []

def post_to_bluesky(banner, client):
    print(f"📥 Downloading: {banner['img']}")
    resp = requests.get(banner['img'], stream=True)
    if resp.status_code != 200:
        return False

    image_data = resp.content
    img_blob = client.upload_blob(image_data)

    embed = {
        "$type": "app.bsky.embed.images",
        "images": [{"alt": banner['text'], "image": img_blob.blob}]
    }

    tb = client_utils.TextBuilder()
    tb.text(f"🔰 NCFC SHOP UPDATE:\n\n{banner['text']}\n\n")
    tb.link("View on Shop", banner['link'])
    tb.text("\n\n#NCFC #Canaries #OTBC")

    try:
        client.send_post(text=tb, embed=embed)
        return True
    except Exception as e:
        print(f"❌ Post Error: {e}")
        return False

def main():
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        print("❌ Error: Secrets not found.")
        return

    seen = load_seen()
    driver = setup_driver()
    
    try:
        found_banners = scrape_banners(driver)
        print(f"📊 Total banners identified: {len(found_banners)}")
        
        if FORCE_POST:
            print("⚡ Force Mode: Ignoring history.")
            to_process = found_banners
        else:
            to_process = [b for b in found_banners if b["id"] not in seen]

        if not to_process:
            print("✅ No new banners today.")
            return

        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

        # Post the first one found
        target = to_process[0]
        if post_to_bluesky(target, client):
            seen.add(target["id"])
            save_seen(seen)
            print(f"🎉 Post successful: {target['text']}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
    
