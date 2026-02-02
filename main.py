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
                return set(json.load(f))
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🏠 Checking Homepage Banners...")
    driver.get(HOME_URL)
    banners = []
    
    try:
        wait = WebDriverWait(driver, 20)
        # We look for common carousel classes
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        time.sleep(5) 

        # Find all homepage links that wrap an image
        items = driver.find_elements(By.CSS_SELECTOR, "a img")
        
        for img_el in items:
            try:
                # Get the link the image points to (parent element)
                link_el = img_el.find_element(By.XPATH, "..")
                link = link_el.get_attribute("href")
                img_url = img_el.get_attribute("src")
                alt_text = img_el.get_attribute("alt") or "New Norwich City Promotion"

                # Filter for actual banner-sized images (ignore small icons)
                if img_url and link and ("banner" in img_url.lower() or "hero" in img_url.lower() or "slider" in img_url.lower()):
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
        print(f"❌ Homepage Scrape Failed: {e}")
        return []

def post_with_image(banner, client):
    print(f"🖼️ Downloading banner: {banner['img']}")
    resp = requests.get(banner['img'])
    if resp.status_code != 200:
        return False

    with open("temp_banner.jpg", "wb") as f:
        f.write(resp.content)

    with open("temp_banner.jpg", "rb") as f:
        img_blob = client.upload_blob(f.read())

    embed = {
        "$type": "app.bsky.embed.images",
        "images": [{"alt": banner['text'], "image": img_blob.blob}]
    }

    tb = client_utils.TextBuilder()
    tb.text(f"🔰 NEW AT THE NCFC SHOP:\n\n{banner['text']}\n\n")
    tb.link("Shop the collection here", banner['link'])
    tb.text("\n\n#NCFC #Canaries #OTBC")

    try:
        client.send_post(text=tb, embed=embed)
        return True
    except Exception as e:
        print(f"❌ Bluesky Post Error: {e}")
        return False

def main():
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        print("❌ Credentials missing.")
        return

    seen = load_seen()
    driver = setup_driver()
    
    try:
        found_banners = scrape_banners(driver)
        
        if FORCE_POST:
            print("⚡ Force Post Active: Ignoring 'seen' history.")
            new_banners = found_banners
        else:
            new_banners = [b for b in found_banners if b["id"] not in seen]

        if not new_banners:
            print("✅ No new banners found.")
            return

        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

        target = new_banners[0]
        if post_with_image(target, client):
            seen.add(target["id"])
            save_seen(seen)
            print("🎉 Success!")

    finally:
        driver.quit()
        if os.path.exists("temp_banner.jpg"):
            os.remove("temp_banner.jpg")

if __name__ == "__main__":
    main()
