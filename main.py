import os
import json
import time
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
PROMO_URL = "https://shop.canaries.co.uk/page/discountsandpromotions"
SEEN_FILE = "seen_promos.json"
KEYWORDS = ["FREE", "% OFF", "SALE", "OFFER", "DISCOUNT", "PRICE DROP", "CLEARANCE", "REDUCED"]

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
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
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def scrape_promos(driver):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🛍️ Accessing Norwich Shop...")
    driver.get(PROMO_URL)
    promos = []
    
    try:
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        time.sleep(5) 
        
        selectors = [".cms-content", "main", "article", ".page-content", "#content", ".container"]
        container = None
        
        for selector in selectors:
            try:
                found = driver.find_element(By.CSS_SELECTOR, selector)
                if found and found.text.strip():
                    container = found
                    print(f"🎯 Found content container using: {selector}")
                    break
            except:
                continue

        search_area = container if container else driver.find_element(By.TAG_NAME, "body")
        elements = search_area.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, p, span")
        
        for el in elements:
            text = el.text.strip()
            if any(kw in text.upper() for kw in KEYWORDS):
                if 10 < len(text) < 400:
                    if "cookie" not in text.lower() and "policy" not in text.lower():
                        if not any(p['headline'] == text for p in promos):
                            promos.append({"headline": text, "url": PROMO_URL})
        
        print(f"📊 Scraper found {len(promos)} unique potential matches.")
        return promos
        
    except Exception as e:
        print(f"❌ Scraping Failed: {e}")
        driver.save_screenshot("error_screenshot.png")
        raise e

def post_to_bluesky(promo, client):
    print(f"📤 Posting to Bluesky: {promo['headline'][:50]}...")
    tb = client_utils.TextBuilder()
    tb.text(f"🛍️ NCFC SHOP DEAL:\n\n{promo['headline']}\n\n")
    tb.link("View details here", promo['url'])
    tb.text("\n\n#NCFC #Canaries #OTBC #NorwichCity")

    try:
        client.send_post(text=tb)
        return True
    except Exception as e:
        print(f"❌ Bluesky Error: {e}")
        return False

def main():
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        print("❌ Error: Missing Bluesky credentials in Environment Secrets.")
        return

    seen = load_seen()
    driver = None
    
    try:
        driver = setup_driver()
        found_promos = scrape_promos(driver)
        
        # Filter for brand new promos
        new_promos = [p for p in found_promos if p["headline"] not in seen]
        
        if not new_promos:
            print("✅ Everything up to date. No new promotions found.")
            return

        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
        
        target = new_promos[0]
        if post_to_bluesky(target, client):
            seen.add(target["headline"])
            save_seen(seen)
            print("🎉 Success! Post updated.")

    except Exception as e:
        print(f"❌ Main Process Error: {e}")
        raise e
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
    
