# CarlaFit

A mobile-friendly fitness class schedule for Carla Madison Recreation Center in Denver, CO.

**Live site:** [gym.breaux.is](https://gym.breaux.is)

## How It Works

A Python script calls the GroupEx Pro API to pull the current class schedule. That data gets saved as a JSON file (a structured text format computers read easily). A GitHub Action runs that script automatically twice a day at 5AM and 5PM Mountain Time. The dashboard reads the JSON file and displays classes grouped by day and time of day.

## Features
- 7-day class schedule with day selector
- Classes grouped by Morning, Afternoon, and Evening
- One-click Google Calendar add for any class
- Class detail view with instructor info
- Weather widget (desktop)
- Installable as a phone app (PWA)

## Files
- `index.html` — The entire dashboard (HTML, CSS, and JS in one file)
- `scripts/scrape_api.py` — Python script that fetches class data from GroupEx Pro API
- `data/schedule.json` — The schedule data the dashboard reads
- `.github/workflows/scrape.yml` — Automation that runs the scraper on a timer
- `manifest.json` — Config that lets the site install as a phone app

## Run It Yourself
1. Clone this repo
2. Get schedule data: `python3 scripts/scrape_api.py`
3. Start a local server: `python3 -m http.server 8000`
4. Open `http://localhost:8000` in your browser
