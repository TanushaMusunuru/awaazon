from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import csv
import os
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__)
app.secret_key = 'secret_key'

def init_files():
    files = {
        'users.csv': ['user_id', 'username', 'email', 'password_hash', 'full_name', 'phone', 'verified'],
        'payment_details.csv': ['user_id', 'card_number', 'card_holder', 'expiry_date', 'cvv', 'billing_address'],
        'orders.csv': ['order_id', 'user_id', 'order_date', 'products', 'total_amount', 'status'],
        'cart_items.csv': ['cart_id', 'user_id', 'product_id', 'product_name', 'quantity', 'price', 'added_date']
    }
    
    for filename, headers in files.items():
        if not os.path.exists(filename):
            with open(filename, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()

init_files()
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

def get_next_id(filename):
    with open(filename, 'r') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        return len(rows) + 1

def add_user(data):
    with open('users.csv', 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['user_id', 'username', 'email', 'password_hash', 'full_name', 'phone', 'verified'])
        writer.writerow(data)

def find_user_by_username(username):
    with open('users.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['username'] == username:
                return row
    return None

def find_user_by_email(email):
    with open('users.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['email'] == email:
                return row
    return None

def update_user_verification(username):
    users = []
    with open('users.csv', 'r') as file:
        reader = csv.DictReader(file)
        users = list(reader)
    
    with open('users.csv', 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['user_id', 'username', 'email', 'password_hash', 'full_name', 'phone', 'verified'])
        writer.writeheader()
        for user in users:
            if user['username'] == username:
                user['verified'] = 'True'
            writer.writerow(user)

def add_payment_details(data):
    with open('payment_details.csv', 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['user_id', 'card_number', 'card_holder', 'expiry_date', 'cvv', 'billing_address'])
        writer.writerow(data)

def get_payment_details(user_id):
    with open('payment_details.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['user_id'] == user_id:
                return row
    return None

def add_order(data):
    with open('orders.csv', 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['order_id', 'user_id', 'order_date', 'products', 'total_amount', 'status'])
        writer.writerow(data)

def get_orders(user_id):
    with open('orders.csv', 'r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader if row['user_id'] == user_id]

def add_to_cart(data):
    with open('cart_items.csv', 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['cart_id', 'user_id', 'product_id', 'product_name', 'quantity', 'price', 'added_date'])
        writer.writerow(data)

def get_cart_items(user_id):
    with open('cart_items.csv', 'r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader if row['user_id'] == user_id]

def clear_cart(user_id):
    cart_items = get_cart_items(user_id)
    if cart_items:
        order_id = get_next_id('orders.csv')
        products = ', '.join([f"{item['product_name']} (x{item['quantity']})" for item in cart_items])
        total_amount = sum(float(item['price']) * int(item['quantity']) for item in cart_items)
        
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'order_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'products': products,
            'total_amount': total_amount,
            'status': 'Processing'
        }
        add_order(order_data)
        
        with open('cart_items.csv', 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['cart_id', 'user_id', 'product_id', 'product_name', 'quantity', 'price', 'added_date'])
            writer.writeheader()
        
        return True
    return False
def validate_email(email):
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def validate_phone(phone):
    import re
    phone_regex = r'^\d{10}$'
    return re.match(phone_regex, phone) is not None

def validate_card_number(card_number):
    import re
    card_regex = r'^\d{15,16}$'
    return re.match(card_regex, card_number) is not None

def validate_cvv(cvv):
    import re
    cvv_regex = r'^\d{3,4}$'
    return re.match(cvv_regex, cvv) is not None

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cart_items = get_cart_items(session['user_id'])
    return render_template('home.html', 
                         username=session.get('username'),
                         cart_count=len(cart_items))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        user = find_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['full_name'] = user['full_name'] 
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        
        # Validation checks
        if not all([username, email, password, confirm_password, full_name]):
            flash('Please fill in all required fields', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('signup.html')
        
        if find_user_by_username(username):
            flash('Username already exists', 'error')
            return render_template('signup.html')
        
        if find_user_by_email(email):
            flash('Email already registered', 'error')
            return render_template('signup.html')
        
        if not validate_email(email):
            flash('Invalid email address', 'error')
            return render_template('signup.html')
        
        if not validate_phone(phone):
            flash('Invalid phone number', 'error')
            return render_template('signup.html')
        
        # Create user account
        user_id = get_next_id('users.csv')
        user_data = {
            'user_id': user_id,
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'full_name': full_name,
            'phone': phone or '',
            'verified': 'True' 
        }
        add_user(user_data)
        payment_data = {
            'user_id': user_id,
            'card_number': '4111111111111111',
            'card_holder': full_name,
            'expiry_date': '12/25',
            'cvv': '123',
            'billing_address': '123 Main St, Anytown, USA'
        }
        add_payment_details(payment_data)
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    payment_details = get_payment_details(user_id)
    orders = get_orders(user_id)
    cart_items = get_cart_items(user_id)
    
    return render_template('dashboard.html', 
                         username=session.get('username'),
                         payment_details=payment_details,
                         orders=orders,
                         cart_items=cart_items)

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    if request.method == 'POST':
        data = request.get_json()
        if not all(key in data for key in ['product_id', 'product_name', 'price', 'quantity']):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
        try:
            price = float(data['price'])
            quantity = int(data['quantity'])
            if price <= 0 or quantity <= 0:
                raise ValueError("Price and quantity must be positive numbers")
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'error': 'Invalid price or quantity'}), 400
        cart = get_cart_items(session['user_id'])
        for item in cart:
            if item['product_id'] == data['product_id']:
                return jsonify({'success': False, 'error': 'Item already in cart'}), 400
        
        cart_data = {
            'cart_id': str(uuid.uuid4()),
            'user_id': session['user_id'],
            'product_id': data['product_id'],
            'product_name': data['product_name'],
            'quantity': quantity,
            'price': price,
            'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        add_to_cart(cart_data)
        
        return jsonify({'success': True, 'message': 'Item added to cart'})
    
    return jsonify({'success': False, 'error': 'Invalid request method'}), 405

@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400
            
        user_id = session['user_id']
        cart_items = get_cart_items(user_id)
        
        updated_cart = [item for item in cart_items if item['product_id'] != product_id]
      
        with open('cart_items.csv', 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['cart_id', 'user_id', 'product_id', 'product_name', 'quantity', 'price', 'added_date'])
            writer.writeheader()
            writer.writerows(updated_cart)
        
        updated_cart_items = get_cart_items(user_id)
        total_price = sum(float(item['price']) * int(item['quantity']) for item in updated_cart_items)
        
        return jsonify({
            'success': True,
            'cart_count': len(updated_cart_items),
            'total_price': total_price,
            'message': 'Item removed from cart successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cart_items = get_cart_items(session['user_id'])
    if not cart_items:
        flash('Your cart is empty!')
        return redirect(url_for('cart'))
    
    total_amount = sum(float(item['price']) * int(item['quantity']) for item in cart_items)
    return render_template('payment.html', cart_items=cart_items, total_amount=total_amount)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.form
    
    if not validate_card_number(data.get('card_number')):
        flash('Invalid card number')
        return redirect(url_for('payment'))
    
    if not validate_cvv(data.get('cvv')):
        flash('Invalid CVV')
        return redirect(url_for('payment'))
    
    payment_data = {
        'user_id': session['user_id'],
        'card_number': data.get('card_number'),
        'card_holder': data.get('card_holder'),
        'expiry_date': data.get('expiry_date'),
        'cvv': data.get('cvv'),
        'billing_address': data.get('billing_address')
    }
    add_payment_details(payment_data)
   
    cart_items = get_cart_items(session['user_id'])
    total_amount = sum(float(item['price']) * int(item['quantity']) for item in cart_items)
    
    order_data = {
        'order_id': str(uuid.uuid4()),
        'user_id': session['user_id'],
        'order_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'products': str(cart_items),
        'total_amount': total_amount,
        'status': 'Processing'
    }
    add_order(order_data)
    
    clear_cart(session['user_id'])
    
    return redirect(url_for('order_confirmation', order_id=order_data['order_id']))

@app.route('/order_confirmation/<order_id>')
def order_confirmation(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with open('orders.csv', 'r') as file:
        reader = csv.DictReader(file)
        order = next((row for row in reader if row['order_id'] == order_id), None)
    
    if not order:
        flash('Order not found')
        return redirect(url_for('dashboard'))
    
    return render_template('order_confirmation.html', order=order)

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cart_items = get_cart_items(session['user_id'])
    
    subtotal = sum(float(item['price']) * int(item['quantity']) for item in cart_items)
    shipping_cost = 0  # Free shipping
    tax_rate = 0.08  # 8% tax
    tax_amount = subtotal * tax_rate
    total = subtotal + shipping_cost + tax_amount
    
    return render_template('cart.html', 
                         username=session.get('username'),
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping_cost=shipping_cost,
                         tax_amount=tax_amount,
                         total=total,
                         cart_count=len(cart_items))

@app.route('/get-cart', methods=['GET'])
def get_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    cart_items = get_cart_items(session['user_id'])
    
    # Calculate totals
    subtotal = sum(float(item['price']) * int(item['quantity']) for item in cart_items)
    shipping_cost = 0  
    tax_rate = 0.08  
    tax_amount = subtotal * tax_rate
    total = subtotal + shipping_cost + tax_amount
    
    return jsonify({
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax_amount': tax_amount,
        'total': total,
        'cart_count': len(cart_items)
    })

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)