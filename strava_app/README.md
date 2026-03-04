# Strava Bike Component Tracker

A personal web app that reads your Strava bicycle rides and lets you track the
usage of individual components (chain, tyres, brake pads, …) on each bike.

## Features

| Feature | Description |
|---------|-------------|
| 🔗 **Strava OAuth** | Connects to your personal Strava account via OAuth 2.0 |
| 🚲 **Bike overview** | Shows all your bikes with their total Strava distances |
| ⚙️  **Component tracking** | Add any component to a bike; the app records the current km total as a baseline |
| 📏 **Usage counter** | See how many km you've ridden since installing / last resetting a component |
| 🔁 **Reset button** | Reset a component's counter when you replace it |
| 🗑 **Delete** | Remove a component that is no longer relevant |
| 🔄 **Auto-sync** | Background job polls Strava every 30 min (configurable); manual "Sync" button also available |

---

## Quick start

### 1. Create a Strava API application

1. Go to <https://www.strava.com/settings/api>
2. Fill in the form (any name / website is fine for personal use)
3. Set **Authorization Callback Domain** to `localhost`
4. Note the **Client ID** and **Client Secret**

### 2. Install dependencies

```bash
cd strava_app
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
export STRAVA_CLIENT_ID="your_client_id"
export STRAVA_CLIENT_SECRET="your_client_secret"
export SECRET_KEY="a-long-random-string"           # optional, has a dev default
export STRAVA_REDIRECT_URI="http://localhost:5000/callback"  # default
export SYNC_INTERVAL_MIN=30                         # optional, default 30
```

### 4. Run the app

```bash
python app.py
```

Open <http://localhost:5000> and click **Connect with Strava**.

---

## How component tracking works

1. Click **＋ Add Component** on a bike card and enter a name (e.g. *Chain*).
2. The app saves the bike's **current total km** as the installation baseline.
3. Every time Strava syncs, the bike's total km is updated.
4. The component card shows **km ridden since installation / last reset**.
5. When you replace a component, hit **🔁 Reset** – this sets the current km
   as the new baseline so the counter restarts from 0.
6. Colour coding:
   - 🟢 Green   → < 1 000 km  (new)
   - 🟡 Orange  → 1 000 – 2 000 km  (monitor)
   - 🔴 Red     → > 2 000 km  (replace soon)

---

## Running tests

```bash
cd strava_app
pytest tests/ -v
```

---

## Project structure

```
strava_app/
├── app.py             # Flask application & routes
├── models.py          # SQLAlchemy database models
├── strava_client.py   # Strava API helpers
├── requirements.txt
├── README.md
├── static/
│   └── style.css      # Application stylesheet
├── templates/
│   ├── base.html      # Shared layout
│   └── index.html     # Main page
└── tests/
    └── test_app.py    # Pytest test suite
```

---

## Environment variable reference

| Variable | Default | Description |
|----------|---------|-------------|
| `STRAVA_CLIENT_ID` | *(required)* | Strava API client ID |
| `STRAVA_CLIENT_SECRET` | *(required)* | Strava API client secret |
| `STRAVA_REDIRECT_URI` | `http://localhost:5000/callback` | OAuth callback URL |
| `SECRET_KEY` | *(dev default)* | Flask session secret – **change in production** |
| `DATABASE_URL` | `sqlite:///strava_app.db` | SQLAlchemy database URL |
| `SYNC_INTERVAL_MIN` | `30` | Background Strava sync interval (minutes) |
