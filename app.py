from flask import Flask, render_template, request, redirect, url_for, flash
from apscheduler.schedulers.background import BackgroundScheduler
from tracker import check_price, get_price, send_email, send_telegram, save_to_csv
from products import save_product, load_products, mark_notified, remove_product
import csv
import config

app = Flask(__name__)
app.secret_key = "gladidzd"

def recheck_all_products():
    for product in load_products():
        if product["notified"]:
            continue
        try:
            price = get_price(product["url"])
            if price is None:
                continue
            save_to_csv(product, price)
            if price < product["target_price"]:
                send_email(product, price)
                send_telegram(product, price)
                mark_notified(product["url"])
                print(f"Price dropped for {product['name']}! Alert sent.")
        except Exception as e:
            print(f"Error checking for {product['name']}: {e}")
scheduler = BackgroundScheduler()
scheduler.add_job(recheck_all_products, 'interval', minutes= 30)
scheduler.start()

def load_prices():
    prices = []
    with open('prices.csv', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            prices.append({
            'date' : row[0],
            'name' : row[1],
            'price' : row[2]
            }) 
    return list(reversed(prices))

def latest_prices():
    latest = {}
    for row in load_prices():
        latest.setdefault(row['name'], row)
    return latest

            
@app.route('/')
def dashboard():
    prices = load_prices()
    products = load_products()
    latest = latest_prices()
    for product in products:
        row = latest.get(product['name'])
        product['current_price'] = row['price'] if row else None
        product['last_checked'] = row['date'] if row else None
    return render_template('index.html', prices=prices, products=products)

@app.route('/add', methods=['POST'])
def add_product():
    product = {
        "name": request.form['name'],
        "url": request.form['url'],
        "target_price": float(request.form['target_price'])
    }
    save_product(product)
    result = check_price(product)
    if result["success"]:
        flash(f"Checked '{product['name']}' — current price ${result['price']}")
    else:
        flash(f"Could not check '{product['name']}': {result['error']}")
    return redirect(url_for('dashboard'))

@app.route('/remove', methods=['POST'])
def remove():
    url = request.form['url']
    remove_product(url)
    flash(f"Removed product with URL: {url}")
    return redirect(url_for('dashboard'))

    
if __name__ =='__main__':
    app.run(debug=True, use_reloader=False)
