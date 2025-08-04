from flask import Flask, render_template, request, session, redirect, url_for
from flask_cors import CORS
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key")

# app.secret_key = "your-secret-key"
CORS(app)




# Admin emails (should match Firebase list)
ADMIN_EMAILS = ["gerald@metohu.com", "metohu.gerald@gmail.com", "info@dynastra.co.uk"]

@app.route('/')
def home():
    return render_template('home.html')  # or whatever your home template is

@app.route('/set-session', methods=['POST'])
def set_session():
    data = request.get_json()
    email = data.get("email")
    session["user_email"] = email
    return "", 204

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get("user_email") not in ADMIN_EMAILS:
        return redirect(url_for("home"))
    return render_template('admin/dashboard.html')

@app.route('/user-dashboard')
def user_dashboard():
    return "<h2>User Dashboard (Non-admin)</h2>"

if __name__ == '__main__':
    app.run(debug=True)
