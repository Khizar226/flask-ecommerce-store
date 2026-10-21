from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-for-sessions'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- STRIPE SETUP ---
# Replace with your actual Stripe Test Secret Key (Get this from dashboard.stripe.com)
stripe.api_key = 'YOUR_STRIPE_SECRET_KEY_HERE' 
YOUR_DOMAIN = 'http://127.0.0.1:5000'

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(250))
    image_url = db.Column(db.String(500))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---
@app.route('/')
def home():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- CART LOGIC ---
@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    
    cart = session['cart']
    cart.append(product_id)
    session['cart'] = cart # Reassign to tell Flask it was modified
    flash('Item added to cart!', 'success')
    return redirect(url_for('home'))

@app.route('/cart')
def view_cart():
    cart_ids = session.get('cart', [])
    cart_items = []
    total_price = 0
    
    for item_id in cart_ids:
        product = Product.query.get(item_id)
        if product:
            cart_items.append(product)
            total_price += product.price
            
    return render_template('cart.html', cart_items=cart_items, total=total_price)

@app.route('/clear-cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('view_cart'))

# --- STRIPE CHECKOUT ---
@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    cart_ids = session.get('cart', [])
    if not cart_ids:
        return redirect(url_for('view_cart'))
        
    line_items = []
    for item_id in cart_ids:
        product = Product.query.get(item_id)
        if product:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                    },
                    'unit_amount': int(product.price * 100), # Stripe expects cents
                },
                'quantity': 1,
            })

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            success_url=YOUR_DOMAIN + '/success',
            cancel_url=YOUR_DOMAIN + '/cancel',
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return str(e)

@app.route('/success')
def success():
    session.pop('cart', None) # Empty the cart after successful payment
    return render_template('success.html')

# --- INITIALIZE DB AND ADD DUMMY PRODUCTS ---
with app.app_context():
    db.create_all()
    if not Product.query.first():
        # Add some sample products for the store
        p1 = Product(name="Python T-Shirt", price=25.00, description="Show off your favorite language!", image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=400&q=80")
        p2 = Product(name="Flask Coffee Mug", price=12.50, description="Perfect for coding sessions.", image_url="https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=400&q=80")
        p3 = Product(name="Mechanical Keyboard", price=99.99, description="Clickity-clack for productivity.", image_url="https://images.unsplash.com/photo-1595225476474-87563907a212?auto=format&fit=crop&w=400&q=80")
        db.session.add_all([p1, p2, p3])
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)