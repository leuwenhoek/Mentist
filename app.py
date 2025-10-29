from flask import Flask
from flask import render_template,redirect

app = Flask(__name__)

@app.route("/")
def redirect_page():
    return redirect("/home")

@app.route("/home")
def home():
    return render_template("home.html") 

if __name__ == "__main__":
    app.run(debug=True)