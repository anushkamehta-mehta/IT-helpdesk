from flask import Blueprint, render_template

bp = Blueprint("employee", __name__)


@bp.route("/tickets")
def my_tickets():
    return render_template("tickets.html")


@bp.route("/tickets/new")
def new_ticket():
    return render_template("new_ticket.html")
