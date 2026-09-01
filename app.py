from flask import Flask, render_template, request, redirect, url_for, flash
from tracker import check_price
import csv
import config

app = Flask(__name__)
app.secret_key = "dev"

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
    return prices
            
@app.route('/')
def dashboard():
    prices = load_prices()
    return render_template('index.html', prices=prices)

@app.route('/add', methods=['POST'])
def add_product():
    product = {
        "name": request.form['name'],
        "url": request.form['url'],
        "target_price": float(request.form['target_price'])
    }
    result = check_price(product)
    if result["success"]:
        flash(f"Checked '{product['name']}' — current price ${result['price']}")
    else:
        flash(f"Could not check '{product['name']}': {result['error']}")
    return redirect(url_for('dashboard'))
    """ name = request.form['name']
    product_url = request.form['url']
    target_price = float(request.form['target_price'])
    print(f"Adding product: {name}, URL: {product_url}, Target Price: {target_price}") """
    

if __name__ =='__main__':
    app.run(debug=True)
