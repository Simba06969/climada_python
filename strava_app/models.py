"""Database models for the Strava bike component tracker."""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class OAuthToken(db.Model):
    """Stores Strava OAuth tokens for the connected athlete."""

    __tablename__ = "oauth_token"

    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(512), nullable=False)
    refresh_token = db.Column(db.String(512), nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)  # Unix timestamp
    athlete_id = db.Column(db.Integer, nullable=True)
    athlete_name = db.Column(db.String(256), nullable=True)


class Bike(db.Model):
    """Represents a bike registered on Strava."""

    __tablename__ = "bike"

    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    distance_m = db.Column(db.Float, default=0.0)  # total lifetime distance in metres
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    components = db.relationship(
        "Component", backref="bike", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def distance_km(self):
        """Total lifetime distance in km."""
        return self.distance_m / 1000.0


class Component(db.Model):
    """A component (e.g. chain) attached to a bike, with km-usage tracking."""

    __tablename__ = "component"

    id = db.Column(db.Integer, primary_key=True)
    bike_id = db.Column(db.Integer, db.ForeignKey("bike.id"), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    # Bike's total distance (metres) when the component was installed or last reset
    distance_at_install_m = db.Column(db.Float, nullable=False)
    installed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_reset_at = db.Column(db.DateTime, nullable=True)

    @property
    def usage_km(self):
        """Kilometres ridden on this bike since the component was installed / reset."""
        return max(0.0, (self.bike.distance_m - self.distance_at_install_m) / 1000.0)
