import os
import datetime

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from cs50 import SQL
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)    

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Generate new list with dict elements
    stocks = db.execute(
        "SELECT symbol, SUM(shares) AS shares, price FROM stocks WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0;", session["user_id"])

    # Store user cash
    user_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    users = db.execute("SELECT * FROM users")
    if len(users)==0:
        return render_template("register.html")
    else:
        # New variable for total cash
        total_cash_stocks = 0

        # Check if user has any shares or not
        if len(stocks) == 0:
            return render_template("index.html", stocks=stocks, user_cash=user_cash[0]["cash"], total_cash=user_cash[0]["cash"])

        else:
            # Iterate over list
            valid_stocks = []
            for stock in stocks:
                quote = lookup(stock["symbol"])
                if quote is None:
                    continue  # skip stocks that can't be looked up
                stock["name"] = quote["name"]
                stock["price"] = quote["price"]
                stock["total"] = stock["price"] * stock["shares"]
                total_cash_stocks += stock["total"]
                valid_stocks.append(stock)

            total_cash = total_cash_stocks + user_cash[0]["cash"]
            return render_template("index.html", stocks=valid_stocks, user_cash=user_cash[0]["cash"], total_cash=total_cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        # Take user input
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        quote = lookup(symbol)

        # Check validity of shares number
        try:
            shares = int(shares)
            if shares < 1:
                return apology("Shares must be a positive integer")
        except ValueError:
            return apology("Shares must be a positive integer")

        # Check validity of symbol
        if not symbol:
            return apology("No symbol")
        elif quote is None:
            return apology("Symbol doesn't exist")
        else:
            user_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

            # Check if user has enough cash
            if user_cash < shares*quote["price"]:
                return apology("Not enough cash to buy the stocks")
            else:
                db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", shares*quote["price"], session["user_id"])
                db.execute("UPDATE users SET stockmoney = stockmoney + ? WHERE id = ?", shares*quote["price"], session["user_id"])
                date = datetime.datetime.now()

                db.execute("INSERT INTO stocks (user_id, symbol, shares, price, date, operation) VALUES (?, ?, ?, ?, ?, ?)",
                           session["user_id"], symbol.upper(), shares, quote["price"], date, "Buy")

                flash("Bought!")
                return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Collect data from stocks table
    stocks = db.execute("SELECT * FROM stocks WHERE user_id = ?", session["user_id"])

    return render_template("history.html", stocks=stocks)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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
    return index()


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Take user input
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        check = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Check user input
        if not username:
            return apology("Please enter a name")

        elif len(check) != 0:
            return apology("Username already exists")

        elif not password:
            return apology("Please enter a password")

        elif not confirmation:
            return apology("Please confirm your passsword")

        elif confirmation != password:
            return apology("Password and Confirm Password do not match")

        # Register user
        else:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username,
                       generate_password_hash(password,  method='pbkdf2:sha256', salt_length=8))
            return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        # Take user input
        symbol = request.form.get("symbol")
        sell_shares = request.form.get("shares")

        # Check validity of shares
        try:
            sell_shares = int(sell_shares)
            if sell_shares < 1:
                return apology("Shares must be a positive integer")
        except ValueError:
            return apology("Shares must be a positive integer")

        # Check validity of symbol
        if not symbol:
            return apology("Missing symbol")

        stocks = db.execute("SELECT SUM(shares) AS shares FROM stocks WHERE user_id = ? AND symbol = ?;",
                            session["user_id"], symbol.upper())[0]

        if sell_shares > stocks["shares"]:
            return apology("You don't have this number of shares")

        # Generate data to be added
        price = lookup(symbol)["price"]
        shares_value = price * sell_shares
        date = datetime.datetime.now()

        # Update table
        db.execute("INSERT INTO stocks (user_id, symbol, shares, price, date, operation) VALUES (?,?,0-?,?,?,?)",
                   session["user_id"], symbol, sell_shares, price, date, "Sell")

        # Update user cash
        db.execute(
            "UPDATE users SET cash = cash + ? WHERE id = ?",
            shares_value,
            session["user_id"],
        )

        flash("Sold!")
        return redirect("/")

    else:
        stocks = db.execute(
            "SELECT symbol FROM stocks WHERE user_id = ? GROUP BY symbol",
            session["user_id"],
        )
        return render_template("sell.html", stocks=stocks)


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def changepassword():
    """Lets user change their password"""
    if request.method == "POST":

        # Take user input
        current = request.form.get("current")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        check = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])

        # Check user input
        if not current:
            return apology("Current Password field cannot be empty")

        elif not password:
            return apology("Please enter a new password")

        elif not confirmation:
            return apology("Please confirm your new passsword")

        elif not check_password_hash(check[0]["hash"], current):
            return apology("Current Password is incorrect")

        elif confirmation != password:
            return apology("Password and Confirm Password do not match")

        # Execute changes
        else:
            db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(
                password,  method='pbkdf2:sha256', salt_length=8), session["user_id"])

            flash("Password changed successfully!")
            return redirect("/")

    else:
        return render_template("change-password.html")

@app.route("/about-us", methods=["GET"])
def aboutus():
    return render_template("about-us.html")

@app.route("/profile", methods=["GET"])
@login_required
def profile():

    name = db.execute("SELECT username FROM users WHERE id=?", session["user_id"])

    stocks = db.execute(
        "SELECT symbol, SUM(shares) AS shares, price FROM stocks WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0;", session["user_id"])

    user_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    # New variable for total cash
    total_cash_stocks = 0

    # Check if user has any shares or not
    if len(stocks) != 0:
        # Iterate over list
        for stock in stocks:
            quote = lookup(stock["symbol"])
            if quote is None:
                continue
            stock["name"] = quote["name"]
            stock["price"] = quote["price"]
            stock["total"] = stock["price"] * stock["shares"]
            total_cash_stocks += stock["total"]

        total_cash = total_cash_stocks + user_cash[0]["cash"]
        profit = total_cash - 12500
    else:
        profit=0
    return render_template("profile.html", name=name[0]['username'], profit=profit, stockmoney=total_cash_stocks)

