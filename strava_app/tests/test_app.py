"""Tests for the Strava bike component tracker app."""

import sys
import os

# Add the strava_app directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from models import Bike, Component, OAuthToken, db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    """Create application for testing with an in-memory database."""
    test_app = create_app(
        test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            },
        }
    )
    with test_app.app_context():
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def connected_app(app):
    """App with a connected Strava account and one bike pre-seeded."""
    with app.app_context():
        token = OAuthToken(
            access_token="test_access",
            refresh_token="test_refresh",
            expires_at=9999999999,
            athlete_id=12345,
            athlete_name="Test Athlete",
        )
        bike = Bike(strava_id="b1001", name="Canyon Ultimate", distance_m=12345.0)
        db.session.add_all([token, bike])
        db.session.commit()
    return app


@pytest.fixture()
def connected_client(connected_app):
    return connected_app.test_client()


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_bike_distance_km(self, app):
        with app.app_context():
            bike = Bike(strava_id="b1", name="Test Bike", distance_m=15000.0)
            db.session.add(bike)
            db.session.commit()
            assert bike.distance_km == pytest.approx(15.0)

    def test_component_usage_km(self, app):
        with app.app_context():
            bike = Bike(strava_id="b2", name="Bike 2", distance_m=10000.0)
            db.session.add(bike)
            db.session.flush()
            comp = Component(
                bike_id=bike.id,
                name="Chain",
                distance_at_install_m=5000.0,  # installed when bike had 5 km
            )
            db.session.add(comp)
            db.session.commit()
            # bike is now at 10 km, installed at 5 km → 5 km usage
            assert comp.usage_km == pytest.approx(5.0)

    def test_component_usage_km_no_negative(self, app):
        with app.app_context():
            bike = Bike(strava_id="b3", name="Bike 3", distance_m=1000.0)
            db.session.add(bike)
            db.session.flush()
            comp = Component(
                bike_id=bike.id,
                name="Tyres",
                distance_at_install_m=2000.0,  # edge-case: install > current
            )
            db.session.add(comp)
            db.session.commit()
            assert comp.usage_km == 0.0

    def test_multiple_components_per_bike(self, app):
        with app.app_context():
            bike = Bike(strava_id="b4", name="Bike 4", distance_m=20000.0)
            db.session.add(bike)
            db.session.flush()
            comps = [
                Component(bike_id=bike.id, name="Chain", distance_at_install_m=0.0),
                Component(bike_id=bike.id, name="Brake pads", distance_at_install_m=10000.0),
            ]
            db.session.add_all(comps)
            db.session.commit()
            assert len(bike.components) == 2


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


class TestIndexRoute:
    def test_index_unauthenticated(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Connect with Strava" in resp.data

    def test_index_authenticated(self, connected_client):
        resp = connected_client.get("/")
        assert resp.status_code == 200
        assert b"Canyon Ultimate" in resp.data
        assert b"12" in resp.data  # ~12 km

    def test_refresh_redirects_without_api(self, connected_client):
        """Refresh with no real API creds should redirect (not crash)."""
        resp = connected_client.get("/refresh", follow_redirects=True)
        assert resp.status_code == 200

    def test_disconnect(self, connected_client, connected_app):
        resp = connected_client.post("/disconnect", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Connect with Strava" in resp.data
        with connected_app.app_context():
            assert OAuthToken.query.count() == 0
            assert Bike.query.count() == 0


class TestComponentRoutes:
    def _get_bike_id(self, app):
        with app.app_context():
            return Bike.query.first().strava_id

    def test_add_component(self, connected_client, connected_app):
        strava_id = self._get_bike_id(connected_app)
        resp = connected_client.post(
            f"/bike/{strava_id}/add_component",
            data={"name": "Chain"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Chain" in resp.data
        with connected_app.app_context():
            assert Component.query.count() == 1
            comp = Component.query.first()
            assert comp.name == "Chain"
            assert comp.distance_at_install_m == pytest.approx(12345.0)

    def test_add_component_empty_name(self, connected_client, connected_app):
        strava_id = self._get_bike_id(connected_app)
        resp = connected_client.post(
            f"/bike/{strava_id}/add_component",
            data={"name": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with connected_app.app_context():
            assert Component.query.count() == 0

    def test_reset_component(self, connected_client, connected_app):
        strava_id = self._get_bike_id(connected_app)
        connected_client.post(
            f"/bike/{strava_id}/add_component",
            data={"name": "Tyres"},
            follow_redirects=True,
        )
        with connected_app.app_context():
            comp_id = Component.query.first().id
            # Component was installed when bike was at 12345 m
            assert Component.query.first().last_reset_at is None

        # Reset the component (bike distance hasn't changed)
        resp = connected_client.post(
            f"/component/{comp_id}/reset", follow_redirects=True
        )
        assert resp.status_code == 200
        with connected_app.app_context():
            comp = db.session.get(Component, comp_id)
            # Reset timestamp should be recorded
            assert comp.last_reset_at is not None
            # After reset, baseline should equal current bike distance
            bike = Bike.query.first()
            assert comp.distance_at_install_m == pytest.approx(bike.distance_m)
            # Usage should be 0 after reset
            assert comp.usage_km == pytest.approx(0.0)

    def test_delete_component(self, connected_client, connected_app):
        strava_id = self._get_bike_id(connected_app)
        connected_client.post(
            f"/bike/{strava_id}/add_component",
            data={"name": "Bar tape"},
            follow_redirects=True,
        )
        with connected_app.app_context():
            comp_id = Component.query.first().id

        resp = connected_client.post(
            f"/component/{comp_id}/delete", follow_redirects=True
        )
        assert resp.status_code == 200
        with connected_app.app_context():
            assert Component.query.count() == 0

    def test_add_component_unknown_bike(self, connected_client):
        resp = connected_client.post(
            "/bike/unknown_id/add_component",
            data={"name": "Chain"},
            follow_redirects=True,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Strava client unit tests (no real network calls)
# ---------------------------------------------------------------------------


class TestStravaClient:
    def test_get_authorization_url(self):
        from strava_client import get_authorization_url

        url = get_authorization_url("12345", "http://localhost:5000/callback")
        assert "strava.com/oauth/authorize" in url
        assert "client_id=12345" in url
        assert "response_type=code" in url
        assert "scope=read,activity:read" in url

    def test_ensure_valid_token_no_refresh_needed(self):
        """ensure_valid_token should return the existing token when it is still valid."""
        import time
        from strava_client import ensure_valid_token

        class FakeToken:
            access_token = "valid_token"
            refresh_token = "ref"
            expires_at = int(time.time()) + 3600  # expires in 1 hour

        token = FakeToken()
        result = ensure_valid_token(token, "cid", "csec")
        assert result == "valid_token"
