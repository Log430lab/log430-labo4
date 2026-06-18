"""
Order manager application
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import threading
from graphene import Schema
from stocks.schemas.query import Query
from flask import Flask, request, jsonify
from orders.controllers.order_controller import create_order, remove_order, get_order, get_report_highest_spending_users, get_report_best_selling_products
from orders.controllers.user_controller import create_user, remove_user, get_user
from stocks.controllers.product_controller import create_product, remove_product, get_product
from stocks.controllers.stock_controller import get_stock, set_stock, get_stock_overview
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Auto-generate Redis reports 2 seconds after startup (to give enough time for the DB to start up as well). Once done for the first time, repeat it recursively every 60s to refresh the cache.
def generate_reports_and_cache():
    threading.Timer(2.0, get_report_highest_spending_users, args=(True,)).start()
    threading.Timer(2.0, get_report_best_selling_products, args=(True,)).start()
    threading.Timer(60.0, generate_reports_and_cache).start()

# Start the first execution
generate_reports_and_cache()

@app.get('/health-check')
def health():
    """Return OK if app is up and running"""
    return jsonify({'status':'ok'})

# Write routes (Commands)
counter_orders = Counter('orders', 'Total calls to /orders')
@app.post('/orders')
def post_orders():
    """Create a new order based on information on request body"""
    counter_orders.inc()
    return create_order(request)

@app.delete('/orders/<int:order_id>')
def delete_orders_id(order_id):
    """Delete an order with a given order_id"""
    return remove_order(order_id)

@app.post('/products')
def post_products():
    """Create a new product based on information on request body"""
    return create_product(request)

@app.delete('/products/<int:product_id>')
def delete_products_id(product_id):
    """Delete a product with a given product_id"""
    return remove_product(product_id)

@app.post('/users')
def post_users():
    """Create a new user based on information on request body"""
    return create_user(request)

@app.delete('/users/<int:user_id>')
def delete_users_id(user_id):
    """Delete a user with a given user_id"""
    return remove_user(user_id)

@app.post('/stocks')
def post_stocks():
    """Set product stock based on information on request body"""
    return set_stock(request)

# Read routes (Queries) 
@app.get('/orders/<int:order_id>')
def get_order_id(order_id):
    """Get order with a given order_id"""
    return get_order(order_id)

@app.get('/products/<int:product_id>')
def get_product_id(product_id):
    """Get product with a given product_id"""
    return get_product(product_id)

@app.get('/users/<int:user_id>')
def get_user_id(user_id):
    """Get user with a given user_id"""
    return get_user(user_id)

@app.get('/stocks/<int:product_id>')
def get_stocks(product_id):
    """Get product stocks by product_id"""
    return get_stock(product_id)

counter_highest_spenders = Counter('highest_spenders', 'Total calls to /orders/reports/highest-spenders')
@app.get('/orders/reports/highest-spenders')
def get_orders_highest_spending_users():
    """Get list of highest speding users, ordered by total expenditure"""
    counter_highest_spenders.inc()
    rows = get_report_highest_spending_users()
    return jsonify(rows)

counter_best_selling_products = Counter('best_selling_products', 'Total calls to /orders/reports/best-sellers')
@app.get('/orders/reports/best-sellers')
def get_orders_report_best_selling_products():
    """Get list of best selling products, ordered by number of orders"""
    counter_best_selling_products.inc()
    rows = get_report_best_selling_products()
    return jsonify(rows)

@app.get('/stocks/reports/overview-stocks')
def get_stocks_overview():
    """Get stocks for all products"""
    rows = get_stock_overview()
    return jsonify(rows)

# Endpoint that allows suppliers to check stock
@app.post('/stocks/graphql-query')
def graphql_supplier():
    data = request.get_json()
    schema = Schema(query=Query)
    result = schema.execute(data['query'], variables=data.get('variables'))
    return jsonify({
        'data': result.data,
        'errors': [str(e) for e in result.errors] if result.errors else None
    })

# TODO: endpoint /metrics Prometheus
@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

# Start Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
