import os
import shutil
import fitz 
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from flask import Flask, request, render_template, flash, redirect, url_for, send_file, session
from flask_pymongo import PyMongo
import bcrypt
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)  
app.secret_key = "supersecretkey" 
app.config["MONGO_URI"] = "mongodb+srv://competition:competition@competition.jhomqki.mongodb.net/database"
mongo = PyMongo(app)
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
POPPLER_PATH = r"C:\\Users\\saran\\OneDrive\\poppler-23.11.0\\Library\\bin"
FOLDER_PATH = "uploads/"  
OUTPUT_PATH = "classified_cases/" 
keywords = {
    "Phishing": ["phish", "email scam", "fake website", "fraudulent email", "credential theft"],
    "Malware": ["malware", "virus", "trojan", "spyware", "worm", "keylogger"],
    "Cyberstalking": ["harass", "threat", "stalking", "blackmail", "cyberbullying"],
    "Banking Fraud": ["fraud", "banking fraud", "credit card scam", "fake transaction", "financial fraud", "internet banking fraud"],
}
OTHER_CATEGORY = "Others"
for category in list(keywords.keys()) + [OTHER_CATEGORY]:
    os.makedirs(os.path.join(OUTPUT_PATH, category), exist_ok=True)
def extract_text(file_path):
    content = ""
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="ISO-8859-1") as f:
            content = f.read().lower()
    elif file_path.endswith(".pdf"):
        try:
            # ✅ Extract text from PDF
            doc = fitz.open(file_path)
            pdf_text = " ".join([page.get_text() for page in doc]).lower()
            doc.close()
            # ✅ Extract text from images inside the PDF using OCR
            try:
                images = convert_from_path(file_path, poppler_path=POPPLER_PATH)
                ocr_text = " ".join(pytesseract.image_to_string(img).lower() for img in images)
            except:
                ocr_text = "" 
            
            content = pdf_text + " " + ocr_text
        except:
            return ""  
    return content

@app.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        action = request.form.get("action") 
        email = request.form["email"]
        password = request.form["password"]
        users = mongo.db.collection_1

        if action == "signup":
           
            if users.find_one({"email": email}):
                flash("Email already registered!", "warning")
                return redirect(url_for("auth"))

            
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            users.insert_one({"email": email, "password": hashed_password})

            flash("Account created! Please log in.", "success")
            return redirect(url_for("auth"))

        elif action == "login":
            user = users.find_one({"email": email})
            if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
                session["email"] = email
                flash("Login successful!", "success")
                return redirect(url_for("index"))
            else:
                flash("Invalid email or password.", "danger")

    return render_template("auth.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("email", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("auth"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "email" not in session:
        return redirect(url_for("auth"))
    if request.method == "POST":
        if "files" not in request.files:
            flash("No file uploaded!", "error")
            return redirect(request.url)

        files = request.files.getlist("files")
        if not files or files[0].filename == "":
            flash("No selected file!", "error")
            return redirect(request.url)

        categorized_files = {}

        for file in files:
            file_path = os.path.join(FOLDER_PATH, file.filename)
            file.save(file_path)
            
            content = extract_text(file_path)
            if not content.strip():
                flash(f"{file.filename} could not be processed!", "error")
                continue  
            category_scores = {cat: 0 for cat in keywords}
            for category, words in keywords.items():
                for word in words:
                    category_scores[category] += content.count(word)
            assigned_category = max(category_scores, key=category_scores.get)
            if all(score == 0 for score in category_scores.values()):
                assigned_category = OTHER_CATEGORY
            dest_path = os.path.join(OUTPUT_PATH, assigned_category, file.filename)
            shutil.move(file_path, dest_path)
            categorized_files.setdefault(assigned_category, []).append(file.filename)
        return render_template("results.html", categorized_files=categorized_files)
    return render_template("index.html")

@app.route("/view/<category>/<filename>")
def view_file(category, filename):
    file_path = os.path.join(OUTPUT_PATH, category, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        return "File not found", 404

if __name__ == "__main__":
    app.run(debug=True)
app.run(debug=True)






