import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Ensure environment variable is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

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
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    # select each symbol owned by the user and it's amount
    portfolio_symbols = db.execute("SELECT shares, symbol \
                                    FROM portfolio WHERE id = :id", \
                                    id=session["user_id"])

    # create a temporary variable to store TOTAL worth ( cash + share)
    total_cash = 0

    # update each symbol prices and total
    for portfolio_symbol in portfolio_symbols:
        symbol = portfolio_symbol["symbol"]
        shares = portfolio_symbol["shares"]
        stock = lookup(symbol)
        total = shares * stock["price"]
        total_cash += total
        db.execute("UPDATE portfolio SET price=:price, \
                    total=:total WHERE id=:id AND symbol=:symbol", \
                    price=usd(stock["price"]), \
                    total=usd(total), id=session["user_id"], symbol=symbol)

    # update user's cash in portfolio
    updated_cash = db.execute("SELECT cash FROM users \
                               WHERE id=:id", id=session["user_id"])

    # update total cash -> cash + shares worth
    total_cash += updated_cash[0]["cash"]

    # print portfolio in index homepage
    updated_portfolio = db.execute("SELECT * from portfolio \
                                    WHERE id=:id", id=session["user_id"])

    return render_template("index.html", stocks=updated_portfolio, \
                            cash=usd(updated_cash[0]["cash"]), total= usd(total_cash) )



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # Ensure there is proper symbol
    if request.method == "GET":
        return render_template("buy.html")

    else:
        quote = lookup(request.form.get("symbol"))

        if not quote:
            return apology("Please enter a valid stock symbol")

        # Ensure proper number of shares
        try:
            share = int(request.form.get("shares"))
            if share < 0:
                return apology("Shares must be positive")
        except:
            return apology("Shares msut be positive integer")
        # Total Amount the user have to pay
        total_amount = quote["price"] * share

        # Taking user's cash in account
        cash = db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])
        if float(cash[0]["cash"]) >= total_amount:
            # Update history table
            # Update do here bro
            # Update cash of user
            db.execute("UPDATE users SET cash = cash - :purchase WHERE id = :id",id=session["user_id"], purchase=(quote["price"] * float(share)))

            # Select the users share of that symbol
            user_share = db.execute("SELECT shares FROM portfolio WHERE id=:id",id=session["user_id"])

            # If there is no stock in user's portfolio
            if not user_share:
                db.execute("INSERT INTO portfolio(id, name, shares, price, total, symbol) VALUES(:id, :name, :shares, :price, :total, :symbol)",id=session["user_id"]
                , name=quote["name"], shares=share, price = usd(quote["price"]), total = usd(total_amount), symbol = quote["symbol"])
            #else increment share count
            else:
                total_shares = user_share[0]["shares"] + share
                db.execute("UPDATE portfolio SET shares = :shares WHERE id = :id AND symbol = :symbol", shares = total_shares, id = session["user_id"], symbol=quote["symbol"])
            return redirect("/")
        else:
            return apology("You Dont have enough cash ", 406)
    # User reach via another route(get)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


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
        quote = lookup(request.form.get("symbol"))
        # Returned a dict eith name , price and symbol of the stock
        if not quote:
            return apology("Please enter a valid stock symbol", 404)
        # redirect to page where portfolio is
        return render_template("quoted.html",  symbol = quote["symbol"], price = quote["price"])
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("please enter the username")
        if not request.form.get("password"):
            return apology("Plaese enter password field")
        if not request.form.get("confirm_password"):
            return apology("please reconfirm password")
        # Confirming both password and confirm password
        if request.form.get("password") != request.form.get("confirm_password"):
            return apology("passwords donot match", 405)
        # Generating hash of password
        hash = generate_password_hash(request.form.get("password"))
        new_key = db.execute("INSERT INTO users (username , hash) VALUES(:username, :hash)", username=request.form.get("username"), hash = hash)
        if not new_key:
            return apology("User already exist", 408)

        # remember which user has logged in
        session["user_id"] = new_key

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        portf = db.execute("SELECT * FROM portfolio WHERE id=:id", id = session["user_id"])
        return render_template("sell.html",portfolio = portf)
    else:

        quote = lookup(request.form.get('stocklist'))
        print(str(quote))
        # Remove the stock frm user's portfolio
        # taking no of shares provided by user in form
        shares = int(request.form.get("no_of_shares"))

        # Taking the price of that share

        price = db.execute("SELECT price FROM portfolio WHERE symbol=:symbol AND id=:id", symbol = quote["symbol"], id = session["user_id"])

        # totla_price
        total_remove_price = shares * quote["price"]
        # Now updating
        print(total_remove_price)
        # Taking total no of shares from portfolio
        share = db.execute("SELECT shares FROM portfolio WHERE id=:id AND symbol=:symbol",symbol =  quote["symbol"],
        id = session["user_id"])
        total = db.execute("SELECT total FROM portfolio WHERE id=:id AND symbol=:symbol",symbol =  quote["symbol"],
        id = session["user_id"])

        # if share provided by user in form is less than or equal to total shares owned then only transaction will processed
        print(share[0]["shares"])
        print(shares)
        if (shares < share[0]["shares"]):
                #  Remove stock and price and no of stocks stocks = stocks - n
                real_total = total[0]["total"].split("$")

                new_total1 = real_total[1][2:]
                new_total2 = real_total[1][:1]
                yup_final = new_total1 + new_total2
                print(yup_final)
                db.execute("UPDATE portfolio set total=:total, shares=:shares WHERE id=:id", total = float(yup_final) - total_remove_price
                , shares = int(share[0]["shares"]) - shares , id=session["user_id"])
                # current selling price = price * stocks and add this to user's cash
        elif (shares == share[0]["shares"]):
            db.execute("DELETE FROM portfolio WHERE id=:id AND symbol=:symbol", id = session["user_id"], symbol =  quote['symbol'])
        else:
            return apology("Unable to process request", 404)
    return redirect("/")

def errorhandler(e):
    """Handle error"""
    return apology("Page not found", 405)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
