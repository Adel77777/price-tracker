import csv
import os

PRODUCTS_FILE = 'products.csv'
FIELDNAMES = ['name', 'url', 'target_price', 'notified']

def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return []
    with open(PRODUCTS_FILE, newline='') as f:
        reader = csv.DictReader(f, fieldnames=FIELDNAMES)

        return [
            {
                "name": row["name"],
                "url": row["url"],
                "target_price": float(row["target_price"]),
                "notified": row["notified"] == "True"
            }
            for row in reader
            if row["name"] != "name"
        ]
def save_product(product):
    file_exists = not os.path.exists(PRODUCTS_FILE) or os.path.getsize(PRODUCTS_FILE) == 0

    with open(PRODUCTS_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(FIELDNAMES)
        writer.writerow([product["name"], product["url"], product["target_price"], False])

def mark_notified(url):
    products = load_products()
    with open(PRODUCTS_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(FIELDNAMES)
        for product in products:
            if product["url"] == url:
                product["notified"] = True
            writer.writerow([product["name"], product["url"], product["target_price"], product["notified"]])

def remove_product(url):
    products = load_products()
    with open(PRODUCTS_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(FIELDNAMES)
        for product in products:
            if product["url"] != url:
                writer.writerow([product["name"], product["url"], product["target_price"], product["notified"]])
