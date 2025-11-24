from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("FRONTEND_SECRET", "dev-secret-key")

# Simple in-memory demo stores (for local demo only)
USERS = {}  # phone -> {phone, name, otp, bank, created_at}
TRANSACTIONS = []  # list of {id, from_phone, to, amount, status, created_at}

BACKEND_URL = os.getenv("BACKEND_URL")  # if set, forms will POST to a real backend


def send_otp(phone: str):
    # Demo: generate numeric OTP and store
    otp = str(uuid.uuid4().int % 1000000).zfill(6)
    USERS.setdefault(phone, {})["otp"] = otp
    # In production: call SMS provider
    print(f"[demo] OTP for {phone}: {otp}")
    return otp


@app.route("/")
def index():
    user = None
    if "phone" in session:
        user = USERS.get(session["phone"]) or {"phone": session["phone"]}
    return render_template("index.html", user=user)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        phone = request.form.get("phone")
        name = request.form.get("name") or ""
        if not phone:
            flash("Phone is required", "error")
            return redirect(url_for("signup"))
        USERS[phone] = {"phone": phone, "name": name, "created_at": datetime.utcnow().isoformat()}
        send_otp(phone)
        flash("OTP sent (check console in demo)", "info")
        return redirect(url_for("verify", phone=phone))
    return render_template("signup.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    phone = request.args.get("phone") or request.form.get("phone")
    if request.method == "POST":
        phone = request.form.get("phone")
        otp = request.form.get("otp")
        user = USERS.get(phone)
        if user and user.get("otp") == otp:
            session["phone"] = phone
            flash("Logged in", "success")
            return redirect(url_for("index"))
        flash("Invalid OTP", "error")
        return redirect(url_for("verify", phone=phone))
    return render_template("verify.html", phone=phone)


@app.route("/logout")
def logout():
    session.pop("phone", None)
    flash("Logged out", "info")
    return redirect(url_for("index"))


@app.route("/link-bank", methods=["GET", "POST"])
def link_bank():
    if "phone" not in session:
        return redirect(url_for("login"))
    phone = session["phone"]
    if request.method == "POST":
        vpa = request.form.get("vpa")
        bank = request.form.get("bank")
        if not vpa:
            flash("VPA or account required", "error")
            return redirect(url_for("link_bank"))
        USERS.setdefault(phone, {})["bank"] = {"vpa": vpa, "bank": bank, "verified": True}
        flash("Bank linked (demo verified)", "success")
        return redirect(url_for("index"))
    return render_template("link_bank.html", user=USERS.get(session["phone"]))


@app.route("/send", methods=["GET", "POST"])
def send_money():
    if "phone" not in session:
        return redirect(url_for("login"))
    phone = session["phone"]
    if request.method == "POST":
        to = request.form.get("to")
        amount = request.form.get("amount")
        try:
            amount_val = float(amount)
        except Exception:
            flash("Invalid amount", "error")
            return redirect(url_for("send_money"))
        txn = {"id": str(uuid.uuid4()), "from": phone, "to": to, "amount": amount_val, "status": "SUCCESS", "created_at": datetime.utcnow().isoformat()}
        TRANSACTIONS.append(txn)
        flash(f"Transaction {txn['id']} created (demo)", "success")
        return redirect(url_for("history"))
    return render_template("send.html")


@app.route("/history")
def history():
    if "phone" not in session:
        return redirect(url_for("login"))
    phone = session["phone"]
    user_txns = [t for t in TRANSACTIONS if t["from"] == phone or t["to"] == phone]
    return render_template("history.html", txns=user_txns)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone")
        if not phone:
            flash("Phone required", "error")
            return redirect(url_for("login"))
        if phone not in USERS:
            flash("Unknown phone. Please signup first.", "error")
            return redirect(url_for("signup"))
        send_otp(phone)
        return redirect(url_for("verify", phone=phone))
    return render_template("login.html")


if __name__ == "__main__":
    host = os.getenv("FRONTEND_HOST", "127.0.0.1")
    port = int(os.getenv("FRONTEND_PORT", 5000))
    app.run(host=host, port=port, debug=True)
