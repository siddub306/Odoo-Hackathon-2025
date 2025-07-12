from flask import Flask, redirect, url_for, render_template
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

app = Flask(__name__)
app.secret_key = "supersecretkey"
google_bp = make_google_blueprint(
    client_id="client-id-here",
    client_secret="client-secretr-here",
    scope=["profile", "email"]
)
app.register_blueprint(google_bp, url_prefix="/login")
class User(UserMixin):
    def __init__(self, id_, name, email):
        self.id = id_
        self.name = name
        self.email = email
login_manager = LoginManager()
login_manager.init_app(app)
users = {}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login/google")
def login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text
    user_info = resp.json()

    user_id = user_info["id"]
    user = User(user_id, user_info["name"], user_info["email"])
    users[user_id] = user
    login_user(user)

    return redirect("/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():
    info = google.get("/oauth2/v2/userinfo").json()
    return f"<h2>Welcome {info['name']} ({info['email']})</h2><br><a href='/logout'>Logout</a>"

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")
@app.route('/register')
def register():
    return render_template('register.html')

if __name__ == "__main__":
    app.run(debug=True)
