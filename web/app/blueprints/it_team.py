from flask import Blueprint, render_template

bp = Blueprint("it_team", __name__, url_prefix="/it")


@bp.route("/tickets")
def all_tickets():
    return render_template("it_tickets.html")
