from flask import Blueprint, render_template

bp = Blueprint("tickets", __name__)


@bp.route("/tickets/<int:ticket_id>")
def detail(ticket_id: int):
    return render_template("ticket_detail.html", ticket_id=ticket_id)
