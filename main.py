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
    # Ensure we save as a list for JSON compatibility
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
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5) 

        # Broad search for banner-like images
        items = driver.find_elements(By.CSS_SELECTOR, "a img")
        
        for img_el in items:
            try:
                link_el = img_el.find_element(By.XPATH, "..")
                link = link_el.get_attribute("href")
                img_url = img_el.get_attribute("src")
                alt_text = img_el.get_attribute("alt") or "Norwich City FC Official Merchandise"

                # Logic to find "Hero" or "Banner" images based on size/keywords
                if img_url and link:
                    url_lower = img_url.lower()
                    if any(x in url_lower for x in ["banner", "hero", "slider", "carousel", "promo"]):
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
    tb.link("View Deal", banner['link'])
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
        
        if FORCE_POST:
            print("⚡ Force Mode: Ignoring history.")
            to_process = found_banners
        else:
            to_process = [b for b in found_banners if b["id"] not in seen]

        if not to_process:
            print("✅ No new banners today.")
            # We still save seen to ensure the file exists for Git
            save_seen(seen)
            return

        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

        # Post the main featured banner
        if post_to_bluesky(to_process[0], client):
            seen.add(to_process[0]["id"])
            save_seen(seen)
            print("🎉 Post successful!")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
    
