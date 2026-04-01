import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol using Twelve Data API.
    Supports both US stocks (e.g. AAPL) and Indian stocks (e.g. TCS, RELIANCE).
    """

    api_key = os.environ.get("API_KEY")
    symbol = symbol.upper().strip()

    # Try plain symbol first, then NSE, then BSE
    attempts = [symbol, f"{symbol}:NSE", f"{symbol}:BSE"]

    for attempt in attempts:
        try:
            url = (
                f"https://api.twelvedata.com/quote"
                f"?symbol={urllib.parse.quote_plus(attempt)}"
                f"&apikey={api_key}"
            )
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "error" or "close" not in data:
                continue

            price = data.get("close") or data.get("previous_close")
            if not price:
                continue

            return {
                "name": data.get("name", attempt),
                "price": float(price),
                "symbol": data.get("symbol", attempt)
            }

        except (requests.RequestException, ValueError, KeyError):
            continue

    return None


def usd(value):
    """Format value as USD."""
    return f"₹{value*80:,.2f}"
