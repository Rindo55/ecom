import os
import uuid
import requests
from flask import Flask, session, render_template, request, redirect, send_from_directory
from flask import Flask, session,render_template,request, Response, redirect, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo import MongoClient
from datetime import datetime
from flask_session import Session
from string import ascii_letters, digits
from helpers import login_required
import random
app = Flask(__name__)

# MongoDB configuration
mongo_uri = "mongodb+srv://dbms:project@cluster0.nyc6v6s.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_uri)
db = client['mydatabase']

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Static file path
@app.route("/static/<path:path>")
def static_dir(path):
    return send_from_directory("static", path)

# Sign up as merchant
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        session.clear()
        password = request.form.get("password")
        repassword = request.form.get("repassword")
        if password != repassword:
            return render_template("error.html", message="Passwords do not match!")

        # Hash password
        pw_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        
        fullname = request.form.get("fullname")
        username = request.form.get("username")
        # Store in database
        usr_id = "".join([random.choice(digits) for n in range(5)])
        new_user = {"customer_id": usr_id, "fullname": fullname, "username": username, "password": pw_hash}
        try:
            db.users.insert_one(new_user)
        except:
            return render_template("error.html", message="Username already exists!")
        return render_template("login.html", msg="Account created!")
    return render_template("signup.html")

# Login as merchant
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()
        username = request.form.get("username")
        password = request.form.get("password")
        result = db.users.find_one({"username": username})
        # Ensure username exists and password is correct
        if result is None or not check_password_hash(result['password'], password):
            return render_template("error.html", message="Invalid username and/or password")
        # Remember which user has logged in
        session["username"] = result['username']
        return redirect("/home")
    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# View all products
@app.route("/")
def index():
    rows = list(db.products.find())
    return render_template("index.html", rows=rows)

# Merchant home page to add new products and edit existing products
@app.route("/home", methods=["GET", "POST"])
@login_required
def home():
    if request.method == "POST":
        image = request.files['image']
        filename = str(uuid.uuid1()) + os.path.splitext(image.filename)[1]
        image.save(os.path.join("static/images", filename))
        pro_id = "".join([random.choice(digits) for n in range(5)])
        with open(os.path.join("static/images", filename), "rb") as file:
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                data={"key": "27b5cf338b8a223e5cafb3f9505808c4"},
                files={"image": file},
            )
        image_url = response.json()["data"]["url"]
        category = request.form.get("category")
        name = request.form.get("pro_name")
        description = request.form.get("description")
        price_range = request.form.get("price_range")
        comments = request.form.get("comments")
        
        new_pro = {
            "pro_id": pro_id,
            "category": category,
            "name": name,
            "description": description,
            "price_range": price_range,
            "filename": image_url,
            "comments": comments,
            "username": session['username']
        }
        db.products.insert_one(new_pro)
        rows = list(db.products.find({"username": session['username']}))
        return render_template("home.html", rows=rows, message="Product added")
    
    rows = list(db.products.find({"username": session['username']}))
    return render_template("home.html", rows=rows)

# When edit product option is selected this function is loaded
@app.route("/edit/<int:pro_id>", methods=["GET", "POST"])
@login_required
def edit(pro_id):
    result = db.products.find_one({"pro_id": pro_id})
    if request.method == "POST":
        # Throw error when some merchant tries to edit product of other merchant
        if result['username'] != session['username']:
            return render_template("error.html", message="You are not authorized to edit this product")
        category = request.form.get("category")
        name = request.form.get("pro_name")
        description = request.form.get("description")
        price_range = request.form.get("price_range")
        comments = request.form.get("comments")
        update_data = {
            "category": category,
            "name": name,
            "description": description,
            "price_range": price_range,
            "comments": comments
        }
        db.products.update_one({"_id": pro_id}, {"$set": update_data})
        rows = list(db.products.find({"username": session['username']}))
        return render_template("home.html", rows=rows, message="Product edited")
    return render_template("edit.html", result=result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8083, debug=True)
