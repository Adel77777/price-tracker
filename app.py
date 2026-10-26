from flask import Flask, render_template, request, redirect, url_for, flash
from apscheduler.schedulers.background import BackgroundScheduler
from tracker import check_price, get_price, send_email, send_telegram, save_to_csv
from products import save_product, load_products, mark_notified, remove_product
import csv
import os
import threading

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cryptic") 

scrape_lock = threading.Lock()

check_status = {}

def check_in_background(product):
    url, name = product["url"], product["name"]
    with scrape_lock:
        try:
            result = check_price(product)
            if result["success"]:
                if result.get("alert"):    
                    mark_notified(url)
                    message = f"Price dropped for '{name}'! Now ${result['price']}, alert sent."
                else:
                    message = f"Checked '{name}': current price ${result['price']}, above your target."
                check_status[url] = {"state": "ok", "message": message}
            else:
                check_status[url] = {"state": "fail", "message": f"Could not check '{name}': {result['error']}"}
        except Exception as e:
            print(f"Background check failed for {name}: {e}", flush=True)
            check_status[url] = {"state": "fail", "message": f"Could not check '{name}': {e}"}

def recheck_all_products():
    for product in load_products():
        if product["notified"]:
            continue
        try:
            with scrape_lock:
                price = get_price(product["url"])
            if price is None:
                continue
            save_to_csv(product, price)
            if price < product["target_price"]:
                try:
                    send_email(product, price)
                except Exception as e:
                    print(f"Email failed: {e}")
                try:
                    send_telegram(product, price)
                except Exception as e:
                    print(f"Telegram failed: {e}")
                mark_notified(product["url"])
                print(f"Price dropped for {product['name']}! Alert sent.")
        except Exception as e:
            print(f"Error checking for {product['name']}: {e}")
scheduler = BackgroundScheduler()
scheduler.add_job(recheck_all_products, 'interval', minutes= 30)
scheduler.start()

def load_prices():
    prices = []
    try:
        with open('prices.csv', 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                prices.append({
                'date' : row[0],
                'name' : row[1],
                'price' : row[2]
                })
    except FileNotFoundError:
        pass 
    return list(reversed(prices))

def latest_prices():
    latest = {}
    for row in load_prices():
        latest.setdefault(row['name'], row)
    return latest

            
@app.route('/')
def dashboard():
    for url, status in list(check_status.items()):
        if status["state"] != "checking":
            flash(status["message"], status["state"])
            del check_status[url]
    checking = any(s["state"] == "checking" for s in check_status.values())
    prices = load_prices()
    products = load_products()
    latest = latest_prices()
    for product in products:
        row = latest.get(product['name'])
        product['current_price'] = row['price'] if row else None
        product['last_checked'] = row['date'] if row else None
    return render_template('index.html', prices=prices, products=products, checking=checking)

@app.route('/add', methods=['POST'])
def add_product():
    product = {
        "name": request.form['name'],
        "url": request.form['url'],
        "target_price": float(request.form['target_price'])
    }
    save_product(product)
    check_status[product["url"]] = {"state": "checking", "message": ""}
    threading.Thread(target=check_in_background, args=(product,), daemon=True).start()
    flash(f"Now tracking '{product['name']}'. Checking the price...", "ok")
    return redirect(url_for('dashboard'))

@app.route('/remove', methods=['POST'])
def remove():
    url = request.form['url']
    remove_product(url)
    flash(f"Removed product with URL: {url}", "ok")
    return redirect(url_for('dashboard'))

    
if __name__ =='__main__':
    app.run(debug=True, use_reloader=False)
