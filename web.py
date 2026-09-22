"""Very small web frontend for the auction skeleton."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from auction import connect, get_auction, list_auctions, place_bid


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
        except ValueError:
            abort(404)
        return render_template("auction.html", auction=auction, bids=bids)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
