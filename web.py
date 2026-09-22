"""Very small web frontend for the auction skeleton."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from auction import (
    auction_has_ended,
    connect,
    create_auction,
    delete_auction,
    get_auction,
    get_winner,
    list_auctions,
    place_bid,
)


PROJECT_DIR = Path(__file__).resolve().parent


def create_app(database: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DATABASE"] = str(database or PROJECT_DIR / "auction.sqlite3")
    app.config["SECRET_KEY"] = "auction-development-key"

    @app.get("/")
    def index():
        with closing(connect(app.config["DATABASE"])) as connection:
            auctions = list_auctions(connection)
        return render_template("index.html", auctions=auctions)

    @app.route("/auction/<auction_id>", methods=["GET", "POST"])
    def auction_page(auction_id: str):
        if request.method == "POST":
            nickname = request.form.get("nickname", "")
            raw_points = request.form.get("points", "")
            try:
                points = int(raw_points)
                with closing(connect(app.config["DATABASE"])) as connection:
                    place_bid(connection, auction_id, nickname, points)
                flash("Ставка сохранена")
                return redirect(url_for("auction_page", auction_id=auction_id))
            except (ValueError, TypeError) as error:
                flash(str(error), "error")

        try:
            with closing(connect(app.config["DATABASE"])) as connection:
                auction, bids = get_auction(connection, auction_id)
                ended = auction_has_ended(auction)
                winner = get_winner(connection, auction_id) if ended else None
        except ValueError:
            abort(404)
        return render_template(
            "auction.html",
            auction=auction,
            bids=bids,
            ended=ended,
            winner=winner,
        )

    @app.route("/auction/new", methods=["GET", "POST"])
    def new_auction():
        if request.method == "POST":
            auction_id = request.form.get("auction_id", "")
            text = request.form.get("text", "")
            raw_lifetime = request.form.get("lifetime_minutes", "")
            try:
                lifetime_minutes = int(raw_lifetime)
                with closing(connect(app.config["DATABASE"])) as connection:
                    create_auction(
                        connection,
                        auction_id,
                        text,
                        lifetime_minutes,
                    )
                flash("Аукцион создан")
                return redirect(url_for("auction_page", auction_id=auction_id.strip()))
            except (ValueError, TypeError) as error:
                flash(str(error), "error")
        return render_template("new_auction.html")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/auction/<auction_id>/delete")
    def delete_auction_page(auction_id: str):
        try:
            with closing(connect(app.config["DATABASE"])) as connection:
                delete_auction(connection, auction_id)
            flash("Аукцион удалён")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
