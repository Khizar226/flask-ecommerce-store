# 🛒 Flask E-Commerce Store

A fully functional e-commerce website built with Python and Flask. Features user authentication, a session-based shopping cart, and secure checkout using the Stripe API.

## 🚀 Features
- **User Authentication:** Register, login, and logout securely using Flask-Login and hashed passwords.
- **Product Catalog:** Display products dynamically from a SQLite database.
- **Shopping Cart:** Add items to a session-based cart.
- **Stripe Checkout:** Integrated with Stripe's payment gateway to process test payments.

## 🛠️ Tech Stack
- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login
- **Frontend:** HTML, Bootstrap 5, Jinja2
- **Database:** SQLite
- **Payment:** Stripe API

## 💻 How to Run Locally
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Add your Stripe Secret Key in `app.py` (Use Test Mode keys).
4. Run the app: `python app.py`
5. Open `http://127.0.0.1:5000` in your browser.