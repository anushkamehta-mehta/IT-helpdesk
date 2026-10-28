from flask import Blueprint, redirect, render_template, url_for

bp = Blueprint("auth", __name__)


@bp.route("/")
def index():
    return redirect(url_for("auth.login"))


@bp.route("/login")
def login():
    return render_template("login.html")


@bp.route("/register")
def register():
    return render_template("register.html")
