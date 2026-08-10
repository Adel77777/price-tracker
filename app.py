from flask import Flask, render_template
import csv

app = Flask(__name__)

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

if __name__ =='__main__':
    app.run(debug=True)
