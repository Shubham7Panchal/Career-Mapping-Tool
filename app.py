from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import current_user, LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this for security
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Load Career Data
career_data = pd.read_csv("data/career_data.csv")

# Career Recommendation Function
def recommend_careers(user_skills):
    user_skills = set(user_skills.lower().split(","))
    recommendations = []
    
    for _, row in career_data.iterrows():
        career_skills = set(row["skills"].lower().split(";"))
        match_score = len(user_skills & career_skills) / len(career_skills)
        
        if match_score > 0:
            recommendations.append((row["career"], match_score, row["recommended_learning"]))
    
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:3]

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists!"}), 400

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    
    return render_template('signup.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    return render_template('login.html')

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Career Recommendation API (Only for Logged-in Users)
@app.route('/recommend', methods=['POST'])
@login_required
def recommend():
    data = request.json
    user_skills = data.get("skills", "")

    if not user_skills:
        return jsonify({"error": "Please provide skills"}), 400

    recommendations = recommend_careers(user_skills)
    return jsonify({"recommendations": recommendations})

# Home Route
@app.route('/')
def home():
    return render_template('index.html', user=current_user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create DB Tables
    app.run(debug=True)

# Add a new model to store user career preferences
class UserCareerPreferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    career_choice = db.Column(db.String(100), nullable=False)
    skills_used = db.Column(db.String(200), nullable=False)

# Create tables in the database
with app.app_context():
    db.create_all()


# Save user career preference
@app.route('/save-career', methods=['POST'])
@login_required
def save_career():
    data = request.json
    career_choice = data.get("career")
    skills_used = data.get("skills")

    if not career_choice or not skills_used:
        return jsonify({"error": "Career choice and skills required"}), 400

    # Save preference in DB
    new_preference = UserCareerPreferences(user_id=current_user.id, career_choice=career_choice, skills_used=skills_used)
    db.session.add(new_preference)
    db.session.commit()
    
    return jsonify({"message": "Career choice saved successfully!"})


@app.route('/dashboard')
@login_required
def dashboard():
    saved_careers = UserCareerPreferences.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', saved_careers=saved_careers)



@app.route('/recommend', methods=['POST'])
@login_required
def recommend():
    data = request.json
    user_skills = data.get("skills", "")

    if not user_skills:
        return jsonify({"error": "Please provide skills"}), 400

    recommendations = recommend_careers(user_skills)
    return jsonify({"recommendations": recommendations})

