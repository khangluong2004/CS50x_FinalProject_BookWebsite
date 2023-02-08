import os

from cs50 import SQL
from datetime import datetime, date
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///booksale.db")




@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    owned = db.execute("SELECT BookName, Price, ForSale, Date, Description FROM book WHERE OwnerID = :user_id", user_id = session["user_id"])
    own = []
    for i in range(len(owned)):
        own.append([owned[i]["BookName"], owned[i]["Price"], owned[i]["ForSale"], owned[i]["Date"], owned[i]["Description"]])
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["cash"]
    return (render_template("index.html", own = own, cash = cash))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        time = datetime.now().strftime("%H:%M:%S")
        day = date.today().strftime("%Y-%m-%d")
        insert = day + " " + time
        bookname = request.form.get("bookname").lower()
        owner = request.form.get("owner")
        number = int(request.form.get("number"))
        check = db.execute("SELECT OwnerName, ForSale, Price, BookName, Description FROM book WHERE OwnerName = :name AND ForSale >= :ForSale AND BookName = :bookname ORDER BY Price", name = owner, ForSale = number, bookname = bookname)
        if len(check) == 0:
            return(apology("Invalid Request"))
        else:
            price = check[0]["Price"]
            cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["cash"]
            cash = cash - check[0]["Price"]
            db.execute("UPDATE users SET cash = :cash WHERE id = :user_id", cash = cash, user_id = session["user_id"])

            owner_cash = db.execute("SELECT cash FROM users WHERE username = :name", name = owner)[0]["cash"]
            owner_cash = owner_cash + check[0]["Price"]
            db.execute("UPDATE users SET cash = :cash WHERE username = :name", cash = owner_cash, name = owner)

            owner_sale = db.execute("SELECT ForSale FROM book WHERE OwnerName = :name AND BookName = :bookname AND Price = :price AND ForSale > 0", name = owner, bookname = bookname, price = price)
            owner_sale = int(owner_sale[0]["ForSale"]) - number
            if owner_sale == 0:
                db.execute("DELETE FROM book WHERE OwnerName = :name AND BookName = :bookname AND Price = :price AND ForSale > 0", name = owner, bookname = bookname, price = price)
            else:
                db.execute("UPDATE book SET ForSale = :ForSale WHERE OwnerName = :name AND BookName = :bookname AND Price = :price AND ForSale > 0", name = owner, bookname = bookname, price = price, ForSale = owner_sale)

            owner_own = db.execute("SELECT ForSale FROM book WHERE OwnerName = :name AND BookName = :bookname AND Price = :price AND ForSale < 0", name = owner, bookname = bookname, price = price)
            owner_own = int(owner_own[0]["ForSale"]) + number
            if owner_own == 0:
                db.execute("DELETE FROM book WHERE OwnerName = :name AND BookName = :bookname AND Price = :price AND ForSale < 0", name = owner, bookname = bookname, price = price)
            else:
                db.execute("UPDATE book SET ForSale = :ForSale WHERE OwnerName = :name AND BookName = :bookname AND Price = :price AND ForSale < 0", name = owner, bookname = bookname, price = price, ForSale = owner_own)

            own = db.execute("SELECT ForSale, BookName, Price FROM book WHERE BookName = :bookname AND Price = :price AND OwnerID = :user_id AND ForSale < 0", user_id = session["user_id"], bookname = bookname, price = price)
            if len(own) == 0:
                name = db.execute("SELECT username FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["username"]
                db.execute("INSERT INTO book (OwnerID, OwnerName, Date, ForSale, BookName, Price, Description) VALUES (?, ?, ?, ?, ?, ?, ?) ", session["user_id"], name, insert, number*-1, bookname, price, check[0]["Description"])
            else:
                db.execute("UPDATE book SET ForSale = :ForSale WHERE BookName = :bookname AND Price = :price AND OwnerID = :user_id AND ForSale < 0", user_id = session["user_id"], bookname = bookname, price = price, ForSale = own[0]["ForSale"] - number)

            db.execute("INSERT INTO history (OwnerID, BookName, Amount, SellBuy, Date) VALUES (?, ?, ?, ?, ?)", session["user_id"], bookname, number, "BUY", insert)
            owner_id = db.execute("SELECT id FROM users WHERE username = :username", username = owner)[0]["id"]
            db.execute("UPDATE history SET SellBuy = :sell, Date = :date WHERE OwnerID = :id AND BookName = :name", sell = "SOLD", date = insert, id = owner_id, name = bookname)
            return(redirect("/"))
    else:
        return(render_template("buy.html"))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    his = db.execute("SELECT * FROM history WHERE OwnerID = :user_id", user_id = session["user_id"])
    record = []
    if len(his) != 0:
        for i in range(len(his)):
            record.append([his[i]["BookName"], his[i]["Amount"], his[i]["SellBuy"], his[i]["Date"]])
    return (render_template("history.html", record = record))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        #Check for name and price of the symbol
        name = str(request.form.get("bookname")).lower()
        if name == None:
            return apology("Invalid name", 400)
        else:
            result = db.execute("SELECT Description, OwnerName, Price, ForSale FROM book WHERE BookName = :BookName AND ForSale >= 1 ORDER BY Price", BookName = name)
            arr = []
            for i in range(len(result)):
                owner = result[i]["OwnerName"]
                price = result[i]["Price"]
                avail = result[i]["ForSale"]
                string = str(avail) + " book(s) called " + str(name).upper() + " is owned by " + str(owner) + " at " + str(usd(price)) + " $. "
                desc = "Description: " + str(result[i]["Description"])
                arr.append([string, desc])
            return render_template("quoted.html", l = arr)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    if request.method == "POST":
        #Validation for input
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif request.form.get("password") != request.form.get("validation"):
            return apology("Incorrect validation", 403)
        #Validation to make sure there is at least 1 capital letters, and 3 numbers
        password = str(request.form.get("password"))
        low_pass = password.lower()
        count = 0
        for i in range(len(password)):
            if password[i].isdigit():
                count = count + 1
        if low_pass == password or count < 3:
            return (apology("Password must have at least 1 uppercase and 3 numbers"))
        #Validation to check if the username is already used
        check = db.execute("SELECT * FROM users WHERE username = :username", username = request.form.get("username"))
        if len(check) == 1:
            return apology("Already used username", 400)
        #Insert the information of new users to the database
        user_id = db.execute("INSERT INTO users(username, hash) VALUES (:username, :hashing)",
        username = request.form.get("username"), hashing = generate_password_hash(request.form.get("password")))
        #Remeber of session
        session["user_id"] = user_id
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add books"""
    if request.method == "POST":
        time = datetime.now().strftime("%H:%M:%S")
        day = date.today().strftime("%Y-%m-%d")
        insert = day + " " + time
        bookname = request.form.get("bookname").lower()
        amount = int(request.form.get("amount"))
        price = request.form.get("price")
        desc = request.form.get("desc")
        check = db.execute("SELECT ForSale FROM book WHERE BookName = :BookName AND OwnerID = :userID AND Price = :price AND ForSale <= 0", userID = session["user_id"], BookName = bookname, price = price)
        if len(check) == 0:
            name = db.execute("SELECT username FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["username"]
            db.execute("INSERT INTO book (OwnerID, OwnerName, Date, ForSale, BookName, Price, Description) VALUES (?, ?, ?, ?, ?, ?, ?) ", session["user_id"], name, insert, amount*-1, bookname, price, desc)
        else:
            num_own = check[0]["ForSale"]
            num_own = num_own - amount
            db.execute("UPDATE book SET ForSale = :ForSale, Date = :Date WHERE BookName = :BookName AND Price = :price AND OwnerID = :userID", ForSale = num_own, userID = session["user_id"], BookName = bookname, Date = insert, price = price)
        return(redirect("/"))
    else:
        return(render_template("add.html"))

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell books"""
    if request.method == "POST":
        desc = request.form.get("description")
        price = request.form.get("price")
        number = int(request.form.get("number"))
        bookname = request.form.get("BookName").lower()
        check = db.execute("SELECT SUM(ForSale) FROM book WHERE BookName = :BookName AND OwnerID = :userID AND ForSale <= 0", userID = session["user_id"], BookName = bookname)
        if len(check) == 0:
            return(render_template("check.html", check = bookname))
        num_own = -1 * check[0]["SUM(ForSale)"]
        if number > num_own:
            return (apology("Insufficient Amount"))
        else:
            time = datetime.now().strftime("%H:%M:%S")
            day = date.today().strftime("%Y-%m-%d")
            insert = day + " " + time

            sold = db.execute("SELECT ForSale FROM book WHERE BookName = :BookName AND Price = :price AND OwnerID = :userID AND ForSale > 0", userID = session["user_id"], BookName = bookname, price = price)
            if len(sold) == 0:
                name = db.execute("SELECT username FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["username"]
                db.execute("INSERT INTO book (OwnerID, OwnerName, Date, ForSale, BookName, Price, Description) VALUES (?, ?, ?, ?, ?, ?, ?) ", session["user_id"], name, insert, number, bookname, price, desc)
            else:
                num_sold = sold[0]["ForSale"]
                num_sold = num_sold + number
                db.execute("UPDATE book SET ForSale = :ForSale, Date = :Date WHERE BookName = :BookName AND Price = :price AND OwnerID = :userID", ForSale = num_sold, userID = session["user_id"], BookName = bookname, Date = insert, price = price)
            db.execute("INSERT INTO history (OwnerID, BookName, Amount, SellBuy, Date) VALUES (?,?,?,?,?)", session["user_id"], bookname, number, "SELL", insert)
            return(redirect("/"))
    else:
        owned = db.execute("SELECT BookName, ForSale FROM book WHERE OwnerID = :userID GROUP BY BookName HAVING SUM(ForSale) < 0", userID = session["user_id"])
        books = []
        for i in range(len(owned)):
            books.append(owned[i]["BookName"])
        return(render_template("sell.html", books = books))


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
