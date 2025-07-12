from flask import Flask, render_template, redirect, url_for, request, session, flash
import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Siddharthdubey0509@2005",
    database="rewear_hackathon"
)

cursor = db.cursor(dictionary=True)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        cursor.execute("SELECT * FROM Users WHERE email = %s AND password_hash = %s", (email, password))
        user = cursor.fetchone()

        if user:
            session['user'] = user["email"]
            session['user_id'] = user["user_id"]
            session['name'] = user["name"]
            session['points'] = user["points"]

            flash("Welcome back!")
            if user["email"] == "admin@rewear.com":
                return redirect(url_for("admin_panel"))
            else:
                return redirect(url_for("main_page"))
        else:
            flash("Invalid email or password.")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if password != confirm:
            flash("Passwords do not match.")
            return render_template("register.html")

        cursor.execute("SELECT * FROM Users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email is already registered.")
            return render_template("register.html")

        cursor.execute("INSERT INTO Users (name, email, password_hash) VALUES (%s, %s, %s)", (name, email, password))
        db.commit()
        flash("Account created! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")



@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    name = session['name']
    points = session['points']

    cursor.execute("SELECT * FROM Item WHERE user_id = %s", (user_id,))
    items = cursor.fetchall()
    cursor.execute("""
        SELECT SwapReq.*, Item.title 
        FROM SwapReq
        JOIN Item ON SwapReq.item_id = Item.item_id
        WHERE from_user_id = %s
        ORDER BY SwapReq.created_at DESC
    """, (user_id,))
    sent_swaps = cursor.fetchall()
    cursor.execute("""
        SELECT SwapReq.*, Users.name AS from_user_name, Item.title 
        FROM SwapReq
        JOIN Users ON SwapReq.from_user_id = Users.user_id
        JOIN Item ON SwapReq.item_id = Item.item_id
        WHERE to_user_id = %s AND SwapReq.status = 'pending'
        ORDER BY SwapReq.created_at DESC
    """, (user_id,))
    received_swaps = cursor.fetchall()

    return render_template("dashboard.html", name=name, points=points, items=items, sent_swaps=sent_swaps, received_swaps=received_swaps)
@app.route("/swap/accept/<int:request_id>")
def accept_swap(request_id):
    if 'user_id' not in session:
        flash("Unauthorized.")
        return redirect(url_for("login"))
    cursor.execute("SELECT item_id FROM SwapReq WHERE request_id = %s", (request_id,))
    req = cursor.fetchone()
    if not req:
        flash("Swap request not found.")
        return redirect(url_for("dashboard"))

    item_id = req["item_id"]
    cursor.execute("UPDATE SwapReq SET status = 'accepted' WHERE request_id = %s", (request_id,))
    cursor.execute("UPDATE SwapReq SET status = 'rejected' WHERE item_id = %s AND status = 'pending' AND request_id != %s", (item_id, request_id))
    cursor.execute("UPDATE Item SET status = 'swapped' WHERE item_id = %s", (item_id,))

    db.commit()
    flash("Swap request accepted. Item marked as swapped.")
    return redirect(url_for("dashboard"))


@app.route("/swap/reject/<int:request_id>")
def reject_swap(request_id):
    cursor.execute("UPDATE SwapReq SET status = 'rejected' WHERE request_id = %s", (request_id,))
    db.commit()
    flash("Swap rejected.")
    return redirect(url_for("dashboard"))



@app.route("/main")
def main_page():
    if 'user_id' not in session:
        flash("Please log in to browse items.")
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT Item.*, Users.name
        FROM Item
        JOIN Users ON Item.user_id = Users.user_id
        WHERE status = 'available'
        ORDER BY created_at DESC
    """)
    items = cursor.fetchall()
    return render_template("main.html", items=items)



@app.route("/item/<int:item_id>")
def item_detail(item_id):
    if 'user_id' not in session:
        flash("Please log in to view item details.")
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT Item.*, Users.name AS uploader_name
        FROM Item
        JOIN Users ON Item.user_id = Users.user_id
        WHERE Item.item_id = %s
    """, (item_id,))
    
    item = cursor.fetchone()

    if not item:
        flash("Item not found.")
        return redirect(url_for('main_page'))

    return render_template("item_detail.html", item=item)
@app.route("/admin")
def admin_panel():
    if 'user_id' not in session or session['user'] != 'admin@rewear.com':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT Item.*, Users.name AS uploader_name
        FROM Item
        JOIN Users ON Item.user_id = Users.user_id
        WHERE Item.status = 'pending'
        ORDER BY Item.created_at DESC
    """)
    items = cursor.fetchall()

    return render_template("admin_panel.html", items=items)


@app.route("/admin/approve/<int:item_id>")
def approve_item(item_id):
    cursor.execute("UPDATE Item SET status = 'available' WHERE item_id = %s", (item_id,))
    db.commit()
    flash("Item approved.")
    return redirect(url_for('admin_panel'))

@app.route("/admin/reject/<int:item_id>")
def reject_item(item_id):
    cursor.execute("UPDATE Item SET status = 'rejected' WHERE item_id = %s", (item_id,))
    db.commit()
    flash("Item rejected.")
    return redirect(url_for('admin_panel'))


@app.route("/account")
def account():
    if 'user_id' not in session:
        flash("Please log in to view your account.")
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor.execute("SELECT name, email, points, created_at FROM Users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    return render_template("account.html", user=user)

@app.route("/swap/<int:item_id>")
def swap_request(item_id):
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    cursor.execute("SELECT user_id FROM Item WHERE item_id = %s", (item_id,))
    item = cursor.fetchone()
    if not item:
        flash("Item not found.")
        return redirect(url_for("main_page"))

    from_user = session['user_id']
    to_user = item['user_id']

    # prevent swapping with self
    if from_user == to_user:
        flash("You can't request swap for your own item.")
        return redirect(url_for("item_detail", item_id=item_id))

    cursor.execute("""
        INSERT INTO SwapReq (from_user_id, to_user_id, item_id, request_type)
        VALUES (%s, %s, %s, 'swap')
    """, (from_user, to_user, item_id))
    db.commit()
    flash("Swap request sent.")
    return redirect(url_for("item_detail", item_id=item_id))

@app.route("/redeem/<int:item_id>")
def redeem_item(item_id):
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    user_id = session['user_id']

    # Get item info
    cursor.execute("SELECT user_id, point_value FROM Item WHERE item_id = %s AND status = 'available'", (item_id,))
    item = cursor.fetchone()
    if not item:
        flash("Item not available.")
        return redirect(url_for("main_page"))

    to_user = item['user_id']
    points_needed = item['point_value']

    # Check user points
    cursor.execute("SELECT points FROM Users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if user['points'] < points_needed:
        flash("Not enough points to redeem.")
        return redirect(url_for("item_detail", item_id=item_id))

    # Deduct points and insert swap request
    cursor.execute("UPDATE Users SET points = points - %s WHERE user_id = %s", (points_needed, user_id))
    cursor.execute("""
        INSERT INTO SwapReq (from_user_id, to_user_id, item_id, request_type)
        VALUES (%s, %s, %s, 'points')
    """, (user_id, to_user, item_id))
    db.commit()
    flash("Redeemed item via points! Awaiting approval.")
    return redirect(url_for("item_detail", item_id=item_id))

@app.route("/add-item", methods=["GET", "POST"])
def add_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        category = request.form.get("category")
        item_type = request.form.get("type")
        size = request.form.get("size")
        condition = request.form.get("condition")
        tags = request.form.get("tags")
        image = request.files.get("image")

        # TODO: Handle image saving and insert into DB here

        flash("Item submitted successfully!")
        return redirect(url_for("dashboard"))

    return render_template("add_item.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
