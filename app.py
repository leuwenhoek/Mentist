# app.py
from flask import Flask, render_template, redirect, request, jsonify
from dotenv import load_dotenv
import os
import google.generativeai as genai
import datetime

load_dotenv()

app = Flask(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

system_instruction = """You are Mentist Bot, a compassionate AI companion for mental wellness. You are here to listen, support, and encourage users. Always be empathetic, non-judgmental, and positive. Remember, you are not a replacement for professional therapy. If the user seems in crisis, gently suggest seeking professional help.

Respond in a warm, friendly tone. Keep responses concise but helpful. End with a question to continue the conversation when appropriate."""
model = genai.GenerativeModel('gemini-1.5-flash-exp', system_instruction=system_instruction)

# Global storage for chat sessions (in-memory; use Redis/DB for production)
chats = {}

@app.route("/")
def redirect_page():
    return redirect("/home")

@app.route("/home")
def home():
    return render_template("home.html") 

@app.route("/mentist-bot")
def bot():
    return render_template("mentist-bot.html")

@app.route("/quiz")
def quiz():
    return render_template("quiz.html")

@app.route("/experts")
def experts():
    return render_template("experts.html")

@app.route("/library")
def library():
    return render_template("library.html")

@app.route("/team")
def myteam():
    return render_template("team.html")
    
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    chat_id = data.get('chat_id')
    
    if not message or not chat_id:
        return jsonify({'error': 'Missing message or chat_id'}), 400
    
    # Initialize chat session if not exists
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