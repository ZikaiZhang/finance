from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

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
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # select from the table history the combination of symbol, sum of shares, price of a user
    rows = db.execute(
        "SELECT symbol, SUM(shares) AS sum, price FROM history WHERE id=:id GROUP BY symbol", id=session["user_id"])

    # create a variable storing the stockasset which is initially 0
    stockasset = 0

    # iterate over each symbol
    for row in rows:

        # look up the web for information about
        quote = lookup(row["symbol"])

        # change the price stored in dict to the current one
        row["price"] = quote["price"]

        # compute the total stockasset
        stockasset += row["price"] * row["sum"]

    # select from the table users the cash for a specific user
    rows2 = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])

    # keep down the cash
    cash = rows2[0]["cash"]

    # compute the total asset
    total = cash + stockasset

    return render_template("index.html", rows=rows, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # check if the input is a valid stock symbol
        if lookup(request.form.get("symbol")) == None:

            # return an apology
            return apology("stock symbol not valid")

        # look up the web for information about a particular stock
        quote = lookup(request.form.get("symbol"))

        # keep down its price
        price = quote["price"]

        # ensure that input value is numeric and keep down the number of shares the user wanna buy
        try:
            shares = int(float(request.form.get("shares")))
        except ValueError:
            return apology("must input a positive integer")

        # check if input value is an integer
        if int(float(request.form.get("shares"))) != float(request.form.get("shares")):

            # return an apology
            return apology("must input a positive integer")

        # sanity check
        if shares < 1:

            # return an apology
            return apology("must input a positive integer")

        # calculate the total amount of money user need to those shares of stock
        total = price * shares

        # query database for cash
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

        # keep down the total cash remaining for the user
        totalremain = rows[0]["cash"]

        # if the user could not afford it
        if total > totalremain:

            # return apology
            return apology("couldn't afford")

        # if the user could afford it
        else:

            # update the cash within the users table
            db.execute("UPDATE users SET cash= :cash WHERE id= :id",
                       cash=totalremain - total, id=session["user_id"])

            # update the history table
            db.execute("INSERT INTO history (id, symbol, price, shares) VALUES(:id, :symbol, :price, :shares)",
                       id=session["user_id"], symbol=quote["symbol"], price=price, shares=shares)

            return redirect("/")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # query database for all information of a user's trasaction
    rows = db.execute("SELECT * FROM history WHERE id=:id", id=session["user_id"])

    # return a webpage displaying transaction information
    return render_template("history.html", rows=rows)


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

    # if user reached route via POST (as by submitting a form via POST) (not sure why using post here)
    if request.method == "POST":

        # check if the input is a valid stock symbol
        if lookup(request.form.get("symbol")) == None:

            # return an apology
            return apology("stock symbol not valid")

        # else return the value for a stock
        quote = lookup(request.form.get("symbol"))

        # return quoted.html
        return render_template("quoted.html", x=quote["name"], y=usd(quote["price"]))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username is submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure confirmation and password are submitted
        elif not request.form.get("confirmation") or not request.form.get("password"):
            return apology("all fields must be filled")

        # ensure password typed in two times are the same
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("passwords do not match")

        # convert the password through a encryption function
        hash = generate_password_hash(request.form.get("password"))

        # insert into database the username and create a variable for validity check
        result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                            username=request.form.get("username"), hash=hash)

        # check if the username is unique
        if result == None:

            # return an apology
            return apology("username used")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect("/")

        # ensure the username chosen is not used
        if not result:
            return apology("username used, try another one")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure that user has a symbol input
        if not request.form.get("symbol"):

            return apology("missing symbol")

        if not request.form.get("shares"):

            return apology("shares")

        # get the symbol to be sold
        symbol = request.form.get("symbol")

        # get the shares to be sold
        shares = int(request.form.get("shares"))

        # ensure that input value is numeric and keep down the number of shares the user wanna buy
        try:
            shares = int(float(request.form.get("shares")))
        except ValueError:
            return apology("must input a positive integer")

        # check if input value is an integer
        if int(float(request.form.get("shares"))) != float(request.form.get("shares")):

            # return an apology
            return apology("must input a positive integer")

        # sanity check
        if shares < 1:

            # return an apology
            return apology("must input a positive integer")

        # get the remaining shares of a particular stock of a user
        rows1 = db.execute("SELECT SUM(shares) AS sum FROM history WHERE id=:id AND symbol=:symbol",
                           id=session["user_id"], symbol=symbol)

        # ensure that there are at least one share of the particular stock
        if rows1[0]["sum"] == 0:

            return apology("no remaining stock")

        # ensure that there are enough stocks left for sell
        if rows1[0]["sum"] < shares:

            return apology("no enough stocks for sell")

        # return the value for a stock
        quote = lookup(request.form.get("symbol"))

        # insert into table history an entry for sell
        db.execute("INSERT INTO history (id, symbol, price, shares) VALUES (:id, :symbol, :price, :shares)",
                   id=session["user_id"], symbol=symbol, price=quote["price"], shares=-shares)

        # query database for cash
        rows3 = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

        # keep down the total cash remaining for the user
        totalremain = rows3[0]["cash"]

        # update the cash in user table
        db.execute("UPDATE users SET cash= :cash WHERE id= :id",
                   cash=totalremain + quote["price"] * shares, id=session["user_id"])

        # return to homepage
        return redirect("/")

    # else if user reached route via GET(as by clicking a link or via redirect)
    else:

        # get different symbols the user bought
        rows2 = db.execute(
            "SELECT symbol FROM history WHERE id=:id GROUP BY symbol", id=session["user_id"])

        return render_template("sell.html", symbols=rows2)


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """allow user to change password"""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # sanity check
        if not request.form.get("password") or not request.form.get("new_password") or not request.form.get("confirmation"):

            # return an apology if one or more fields miss input
            return apology("all fields must be filled")

        # check if two passwords entered are the same
        if request.form.get("new_password") != request.form.get("confirmation"):

            # return an apology if new passwords don't match
            return apology("new passwords don't match")

        # convert the password through a encryption function
        hash = generate_password_hash(request.form.get("new_password"))

        # get the hash value for password from the database
        rows = db.execute("SELECT hash FROM users WHERE id=:id", id=session["user_id"])

        # store the hash value for the original password
        #hash_original = rows[0]["hash"]

        # check if input for original password is correct
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):

            # return an apology
            return apology("input for original password incorrect")

        db.execute("UPDATE users SET hash= :hash WHERE id= :id", hash=hash, id=session["user_id"])

        # return to homepage
        return redirect("/")

    # Redirect user to index page
    else:
        return render_template("change_password.html")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
