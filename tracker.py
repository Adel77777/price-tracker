from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import smtplib
from email.mime.text import MIMEText
import time
import config

def get_price(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    # Force English language
    options.add_argument("--lang=en-US")
    options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })

    driver = webdriver.Chrome(options=options)

    try:
        # Set cookies BEFORE loading any page
        driver.get("https://www.aliexpress.com")
        
        # Override the site/locale cookies directly
        driver.add_cookie({"name": "aep_usuc_f", "value": "site=glo&c_tp=USD&b_locale=en_US&region=DZ", "domain": ".aliexpress.com"})
        driver.add_cookie({"name": "aep_usuc_f", "value": "site=glo&c_tp=USD&b_locale=en_US&region=DZ", "domain": ".aliexpress.com", "path": "/"})

        # Reload with cookies set
        driver.get("https://www.aliexpress.com")
        time.sleep(2)

        driver.get(url)

        price_tag = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span[class*="price-default--current"]'))
        )
        price = price_tag.text.strip().replace("US", "").replace("$", "").strip()
        return float(price)

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        driver.quit()

url = "https://www.aliexpress.com/item/1005010279002187.html"

def check_price():
    current_price = get_price(config.URL)
    if current_price is None:
        print("Could not retrieve the price.")
        return
    elif current_price < config.TARGET_PRICE:
        print(f"Price dropped to ${current_price}! Sending alert...")
        send_email(current_price)
    else:
        print(f"Price is ${current_price} — above target")
    
def send_email(current_price):
    subject = "Price Alert: Item Price Dropped!"
    body = f"Good news! The price dropped to ${current_price}. \n Check it out here: {config.url}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_SENDER
    msg["To"] = config.EMAIL_RECEIVER

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
        server.sendmail(config.EMAIL_SENDER, config.EMAIL_RECEIVER, msg.as_string())
        print("Email sent successfully!")

while True:
    check_price()
    print(f"Waiting {config.CHECK_INTERVAL} seconds before next check...")
    time.sleep(config.CHECK_INTERVAL)