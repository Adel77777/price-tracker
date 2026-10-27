import threading
import atexit
import time
import config
import csv
import requests
import os
import re
import smtplib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# setting up cookies & domain
COOKIE = {
    "name": "aep_usuc_f",
    "value": "site=glo&c_tp=USD&b_locale=en_US&region=DZ",
    "domain": ".aliexpress.com",
    "path": "/",
}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MAX_SCRAPES_PER_BROWSER = 25

_scrape_lock = threading.Lock()   
_driver = None                    
_scrapes = 0


#building webdriver with necessary options

def _build_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--lang=en-US")
    options.add_argument("--window-size=1366,768")
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.page_load_strategy = "eager"
    options.add_experimental_option("prefs", {
        "intl.accept_languages": "en-US,en",
        "profile.managed_default_content_settings.images": 2,
    })

    chrome_bin = os.environ.get("CHROME_BIN")
    driver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chrome_bin:
        options.binary_location = chrome_bin
    service = webdriver.ChromeService(executable_path=driver_path) if driver_path else None
    driver = webdriver.Chrome(service=service, options=options) if service else webdriver.Chrome(options=options)

    driver.set_page_load_timeout(30)
    # Set the locale cookie directly, without loading the homepage first
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.setCookie", COOKIE)
    return driver


def _close_driver():
    global _driver
    try:
        if _driver is not None:
            _driver.quit()
    except Exception:
        pass
    _driver = None


atexit.register(_close_driver)


def _get_driver():
    global _driver, _scrapes
    if _driver is not None and _scrapes >= MAX_SCRAPES_PER_BROWSER:
        _close_driver()        
    if _driver is not None:
        try:
            _driver.title        
        except Exception:
            _close_driver()
    if _driver is None:
        _driver = _build_driver()
        _scrapes = 0
    return _driver


# Price scraping function with error block handling & logging
def get_price(url):
    global _scrapes
    match = re.search(r"/item/(\d+)\.html", url)
    if match:
        url = f"https://www.aliexpress.com/item/{match.group(1)}.html"

    with _scrape_lock:
        t0 = time.time()
        try:
            driver = _get_driver()
            _scrapes += 1
            driver.get(url)
            price_tag = WebDriverWait(driver, 10, poll_frequency=0.2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span[class*="price-default--current"]'))
            )
            price = price_tag.text.strip().replace("US", "").replace("$", "").strip()
            print(f"Scrape took {time.time() - t0:.1f}s", flush=True)
            return float(price)
        except Exception as e:
            print(f"Error: {type(e).__name__} after {time.time() - t0:.1f}s", flush=True)
            _close_driver()      
            return None

def send_alerts(product, price):
    def run(label, fn):
        try:
            fn(product, price)
        except Exception as e:
            print(f"{label} failed: {e}", flush=True)

    jobs = [
        threading.Thread(target=run, args=("Email", send_email)),
        threading.Thread(target=run, args=("Telegram", send_telegram)),
    ]
    for job in jobs:
        job.start()
    for job in jobs:
        job.join()

def check_price(product):
    current_price = get_price(product["url"])
    if current_price is None:
        return {"success": False, "error": "Could not retrieve price"}
    
    save_to_csv(product, current_price)

    result = {"success": True, "price": current_price, "name": product["name"]}

    if current_price < product['target_price']:
        print(f"Price dropped to ${current_price}! Sending alert...")
        send_alerts(product, current_price)
        result["alert"] = True
    else:
        print(f"Price is ${current_price} — above target", flush=True)
    return result
    
def send_email(product, current_price):
    subject = "🔔Price Alert: Item Price Dropped!"
    #body = f"Good news! The price of {product['name']} dropped to ${current_price}. \n Check it out here: {product['url']}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_SENDER
    msg["To"] = config.EMAIL_RECEIVER

    with open("templates/email_template.html", "r", encoding="UTF-8") as f:
        html = f.read()

    html = html.replace("{{name}}", product["name"].upper())
    html = html.replace("{{price}}", f"${current_price}")
    html = html.replace("{{url}}", product["url"])

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        server.starttls()
        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
        server.sendmail(config.EMAIL_SENDER, config.EMAIL_RECEIVER, msg.as_string())
        print("Email sent successfully!")
    

def send_telegram(product, current_price):
    token = config.TELEGRAM_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID
    message = f"Price alert! {product['name']} dropped to ${current_price}. Check it out here: {product['url']}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
    print("Telegram message sent successfully!")


def save_to_csv(product, current_price):
    with open('prices.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product['name'], current_price])
if __name__ == "__main__":
    while True:
        for product in config.PRODUCTS:
            check_price(product)
        print(f"Waiting {config.CHECK_INTERVAL} seconds before next check...")
        time.sleep(config.CHECK_INTERVAL)



