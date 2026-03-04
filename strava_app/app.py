"""Flask application – Strava bike component tracker.

Environment variables
---------------------
STRAVA_CLIENT_ID      Strava API application client ID  (required)
STRAVA_CLIENT_SECRET  Strava API application client secret  (required)
STRAVA_REDIRECT_URI   OAuth callback URL  (default: http://localhost:5000/callback)
SECRET_KEY            Flask secret key  (default: dev key – change in production!)
DATABASE_URL          SQLAlchemy database URL  (default: sqlite:///strava_app.db)
SYNC_INTERVAL_MIN     Background sync interval in minutes  (default: 30)
"""

import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, flash, redirect, render_template, request, url_for
import requests

from models import Bike, Component, OAuthToken, db
from strava_client import ensure_valid_token, exchange_code, get_athlete, get_authorization_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///strava_app.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    _register_routes(app)
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET", "")
STRAVA_REDIRECT_URI = os.environ.get(
    "STRAVA_REDIRECT_URI", "http://localhost:5000/callback"
)
SYNC_INTERVAL_MIN = int(os.environ.get("SYNC_INTERVAL_MIN", "30"))


def _get_token():
    """Return the single stored OAuthToken row, or None."""
    return OAuthToken.query.first()


def _sync_bikes_from_strava(app: Flask):
    """Background-safe: fetch latest bike distances from Strava and update DB."""
    with app.app_context():
        token = _get_token()
        if token is None:
            return
        try:
            access_token = ensure_valid_token(token, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET)
            db.session.commit()  # persist refreshed tokens if any

            athlete = get_athlete(access_token)
            for gear in athlete.get("bikes", []):
                strava_id = gear["id"]
                bike = Bike.query.filter_by(strava_id=strava_id).first()
                if bike is None:
                    bike = Bike(strava_id=strava_id, name=gear["name"])
                    db.session.add(bike)
                bike.name = gear["name"]
                bike.distance_m = float(gear.get("distance", 0))
                bike.last_updated = datetime.now(timezone.utc)
            db.session.commit()
            logger.info("Strava sync completed successfully.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Strava sync failed: %s", exc)
            db.session.rollback()


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def _register_routes(app: Flask):  # noqa: C901  (many routes is expected)

    # -- Authentication ------------------------------------------------------

    @app.route("/auth")
    def auth():
        if not STRAVA_CLIENT_ID:
            flash("STRAVA_CLIENT_ID is not set. Please check your configuration.", "error")
            return redirect(url_for("index"))
        url = get_authorization_url(STRAVA_CLIENT_ID, STRAVA_REDIRECT_URI)
        return redirect(url)

    @app.route("/callback")
    def callback():
        error = request.args.get("error")
        if error:
            flash(f"Strava authorisation failed: {error}", "error")
            return redirect(url_for("index"))

        code = request.args.get("code")
        if not code:
            flash("No authorisation code received from Strava.", "error")
            return redirect(url_for("index"))

        try:
            data = exchange_code(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, code)
        except requests.RequestException as exc:
            flash(f"Token exchange failed: {exc}", "error")
            return redirect(url_for("index"))

        # Persist / update the single token record
        token = OAuthToken.query.first()
        if token is None:
            token = OAuthToken()
            db.session.add(token)
        token.access_token = data["access_token"]
        token.refresh_token = data["refresh_token"]
        token.expires_at = data["expires_at"]
        athlete = data.get("athlete", {})
        token.athlete_id = athlete.get("id")
        token.athlete_name = (
            f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
        )
        db.session.commit()

        _sync_bikes_from_strava(app)
        flash("Connected to Strava successfully!", "success")
        return redirect(url_for("index"))

    @app.route("/disconnect", methods=["POST"])
    def disconnect():
        OAuthToken.query.delete()
        Bike.query.delete()
        db.session.commit()
        flash("Disconnected from Strava. All data has been removed.", "info")
        return redirect(url_for("index"))

    # -- Main page -----------------------------------------------------------

    @app.route("/")
    def index():
        token = _get_token()
        if token is None:
            return render_template(
                "index.html", connected=False, sync_interval=SYNC_INTERVAL_MIN
            )
        bikes = Bike.query.order_by(Bike.name).all()
        last_synced = max((b.last_updated for b in bikes), default=None)
        return render_template(
            "index.html",
            connected=True,
            athlete_name=token.athlete_name,
            bikes=bikes,
            last_synced=last_synced,
            sync_interval=SYNC_INTERVAL_MIN,
        )

    # -- Manual Strava sync --------------------------------------------------

    @app.route("/refresh")
    def refresh():
        _sync_bikes_from_strava(app)
        flash("Bikes refreshed from Strava.", "success")
        return redirect(url_for("index"))

    # -- Component management ------------------------------------------------

    @app.route("/bike/<strava_bike_id>/add_component", methods=["POST"])
    def add_component(strava_bike_id: str):
        bike = Bike.query.filter_by(strava_id=strava_bike_id).first_or_404()
        name = request.form.get("name", "").strip()
        if not name:
            flash("Component name cannot be empty.", "error")
            return redirect(url_for("index"))
        component = Component(
            bike_id=bike.id,
            name=name,
            distance_at_install_m=bike.distance_m,
        )
        db.session.add(component)
        db.session.commit()
        flash(f'Component "{name}" added to {bike.name}.', "success")
        return redirect(url_for("index"))

    @app.route("/component/<int:component_id>/reset", methods=["POST"])
    def reset_component(component_id: int):
        component = db.get_or_404(Component, component_id)
        component.distance_at_install_m = component.bike.distance_m
        component.last_reset_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'Component "{component.name}" has been reset.', "success")
        return redirect(url_for("index"))

    @app.route("/component/<int:component_id>/delete", methods=["POST"])
    def delete_component(component_id: int):
        component = db.get_or_404(Component, component_id)
        name = component.name
        db.session.delete(component)
        db.session.commit()
        flash(f'Component "{name}" has been deleted.', "info")
        return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=_sync_bikes_from_strava,
        args=[app],
        trigger="interval",
        minutes=SYNC_INTERVAL_MIN,
        id="strava_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Background sync scheduler started (interval: %d min).", SYNC_INTERVAL_MIN
    )
    try:
        app.run(debug=False, use_reloader=False)
    finally:
        scheduler.shutdown()
