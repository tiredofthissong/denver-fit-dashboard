# CarlaFit Dashboard

Premium mobile-first fitness schedule for Carla Madison Rec Center.

## Features
- 📅 Google Calendar integration (one-click add)
- 🎨 Category-specific colors & emoji icons
- 📱 Day/Week view toggle
- 🗺️ Location embedded in calendar invites
- 🌐 Works on any device with any Google account

## Deploy

1. Upload all files to your `denver-fit-dashboard` repo
2. Go to **Actions → Daily Schedule Scrape → Run workflow**
3. Visit `gym.breaux.is` after ~60 seconds

## Files
- `index.html` — Dashboard (GitHub Pages)
- `scrape.py` — Data scraper
- `.github/workflows/scrape.yml` — Auto-updates (5AM/5PM MT)
- `manifest.json` — PWA config
- `requirements.txt` — Python deps
