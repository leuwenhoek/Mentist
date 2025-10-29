# app.py
from flask import Flask, render_template, redirect, request, jsonify, session, url_for
from flask_session import Session # For server-side session management
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash # For password hashing
import os
import google.generativeai as genai
import sqlite3
import datetime
import uuid # For generating unique session IDs
import functools

load_dotenv()

app = Flask(__name__)

# --- Flask Session Configuration (REQUIRED FOR LOGIN) ---
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem" # Stores sessions in a local file
Session(app)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# --- Database Configuration ---
DB_NAME = 'mentist_users.db'

def init_db():
    """Initializes the SQLite database and creates the users table."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database when the app starts
with app.app_context():
    init_db()

# Global storage for chat sessions (in-memory; use Redis/DB for production)
chats = {}

system_instruction = """You are Mentist Bot, a compassionate AI companion for mental wellness. You are here to listen, support, and encourage users. Always be empathetic, non-judgmental, and positive. Remember, you are not a replacement for professional therapy. If the user seems in crisis, gently suggest seeking professional help.

Respond in a warm, friendly tone. Keep responses concise but helpful. End with a question to continue the conversation when appropriate."""
model = genai.GenerativeModel('gemini-1.5-flash-exp', system_instruction=system_instruction)

# --- Authentication Helpers ---
def login_required(f):
    """A decorator to ensure the user is logged in before accessing a route."""
    @functools.wraps(f) 
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Flash message could be added here
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- New User Authentication Routes ---

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handles user login and registration forms."""
    if request.method == "POST":
        form_type = request.form.get("form_type")
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email") # Only used for registration

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        if form_type == "register":
            if not username or not email or not password:
                return render_template("login.html", error="All fields are required for registration.", active_tab="register")
            
            try:
                password_hash = generate_password_hash(password)
                c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", 
                          (username, email, password_hash))
                conn.commit()
                # Auto-login after successful registration
                user_id = c.lastrowid
                session['user_id'] = user_id
                session['username'] = username
                return redirect("/home")
            except sqlite3.IntegrityError:
                return render_template("login.html", error="Username or Email already exists.", active_tab="register")
            except Exception as e:
                return render_template("login.html", error=f"An error occurred during registration: {e}", active_tab="register")

        elif form_type == "login":
            if not username or not password:
                return render_template("login.html", error="Username and Password are required.", active_tab="login")
            
            c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            conn.close()

            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['username'] = username
                # Redirect to the home page or the page they tried to access
                return redirect(request.args.get('next') or "/home")
            else:
                return render_template("login.html", error="Invalid username or password.", active_tab="login")

    # GET request
    return render_template("login.html", active_tab="login")


@app.route("/logout")
def logout():
    """Logs the user out by clearing the session."""
    session.clear()
    return redirect("/login")


# --- Existing Application Routes (Now protected) ---

@app.route("/")
@login_required
def redirect_page():
    # Only logged-in users can access this. Redirects to login if not.
    return redirect("/home")

@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session.get('username')) 

@app.route("/mentist-bot")
@login_required
def bot():
    # Use a unique chat_id for each user session
    if 'chat_id' not in session:
        session['chat_id'] = str(uuid.uuid4())
    return render_template("mentist-bot.html", chat_id=session['chat_id'])

@app.route("/quiz")
@login_required
def quiz():
    return render_template("quiz.html")

@app.route("/experts")
@login_required
def experts():
    return render_template("experts.html")

@app.route("/library")
@login_required
def library():
    return render_template("library.html")

@app.route("/team")
@login_required
def myteam():
    return render_template("team.html")
    
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    # The chat logic remains largely the same, but now it's protected
    data = request.json
    message = data.get('message')
    
    # We use the chat_id from the session instead of relying on the client
    chat_id = session.get('chat_id')
    
    if not message or not chat_id:
        return jsonify({'error': 'Missing message or chat session'}), 400
    
    # Initialize chat session if not exists
    # Key it by the session chat_id to maintain conversation history
    if chat_id not in chats:
        chats[chat_id] = model.start_chat()
    
    try:
        response = chats[chat_id].send_message(message)
        bot_response = response.text
    except Exception as e:
        bot_response = 'I apologize, but I encountered an error. Please try again.'
        print(f"Gemini error: {e}")
    
    return jsonify({'response': bot_response})

if __name__ == "__main__":
    app.run(debug=True)