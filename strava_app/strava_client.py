"""Strava API client helpers."""

import time

import requests

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


def get_authorization_url(client_id: str, redirect_uri: str) -> str:
    """Return the Strava OAuth authorization URL."""
    params = (
        f"client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&approval_prompt=auto"
        "&scope=read,activity:read"
    )
    return f"{STRAVA_AUTH_URL}?{params}"


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange an authorisation code for access + refresh tokens.

    Returns a dict with keys: access_token, refresh_token, expires_at,
    athlete (sub-dict).
    """
    resp = requests.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Refresh an expired access token.

    Returns a dict with keys: access_token, refresh_token, expires_at.
    """
    resp = requests.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_athlete(access_token: str) -> dict:
    """Fetch the authenticated athlete's profile (includes bikes under 'bikes')."""
    resp = requests.get(
        f"{STRAVA_API_BASE}/athlete",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def ensure_valid_token(token_row, client_id: str, client_secret: str) -> str:
    """Return a valid access token, refreshing it if it has expired.

    *token_row* is an ``OAuthToken`` model instance.  The instance is updated
    in-place; the caller is responsible for committing the session.
    """
    # Refresh if the token expires within the next 60 seconds
    if int(time.time()) >= token_row.expires_at - 60:
        data = refresh_access_token(client_id, client_secret, token_row.refresh_token)
        token_row.access_token = data["access_token"]
        token_row.refresh_token = data["refresh_token"]
        token_row.expires_at = data["expires_at"]
    return token_row.access_token
