# EuroMillions Duplet Analyzer

Scrapes the "most common main number pairs" table from
https://lottery.merseyworld.com/Euro/Analysis/Pairs.html, stores it locally,
and lets you check which pairs formed from a set of numbers have appeared
historically.

## How it works

1. You enter a set of numbers (e.g. the 5 main numbers from a draw: `7 14 28 42 45`).
2. The backend generates every possible 2-number combination ("duplet") from them.
3. It checks each duplet against the locally stored historical pair data and
   returns two things:
   - **All generated duplets** — every pair formed from your numbers.
   - **Matches found in historical data** — the subset of those pairs that
     appear in the source site's data, with how many times each has been drawn.

You choose whether to use the locally stored snapshot or trigger a fresh
scrape of the live site first.

## Important limitation (from the source site itself)

The source page only lists **individual pair identities for frequency bands
above a threshold** (currently pairs that occurred more than ~15 times — 664
out of the 1225 possible pairs, as of the last check). For pairs that occurred
15 times or fewer, the site only gives an aggregate count per frequency band,
not which specific pairs they are. So a duplet showing up as "not matched"
does **not** mean it never occurred — it means it's not in the top-frequency
list this site publishes. This is a limitation of the data source, not the tool.

## Project structure

```
backend/            FastAPI app (scraper + API)
  main.py
  scraper.py
  database.py
  requirements.txt
  render.yaml
frontend/            Plain HTML/CSS/JS (no framework)
  index.html
  style.css
  app.js
  config.js           <- set your backend URL here after deploying
  vercel.json
```

## Running locally

Backend:
```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend: just open `frontend/index.html` in a browser (or serve it with
any static file server), with `config.js` pointing at
`http://localhost:8000`.

First thing to do: click **"Refresh data now"** once to populate the local
database from the live site (this requires internet access to
lottery.merseyworld.com from wherever the backend runs).

## Deploying

**Backend -> Render**
1. Push this repo to GitHub.
2. In Render, create a new Web Service pointing at the `backend/` folder
   (or use the included `render.yaml`).
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Note: Render's free tier disk is not persistent across deploys, so the
   SQLite file resets on redeploy — just click "Refresh data now" again
   after a redeploy, it only takes a couple of seconds.

**Frontend -> Vercel**
1. Deploy the `frontend/` folder as a static site (no build step needed).
2. Edit `config.js` and set `API_BASE_URL` to your Render backend URL
   (e.g. `https://euromillions-duplet-backend.onrender.com`) **before**
   deploying, or edit it in the Vercel dashboard's file editor / redeploy
   after editing.

## API endpoints (backend)

- `GET /api/status` — last scrape time and how many pairs are stored.
- `POST /api/scrape` — re-scrapes the live site and overwrites stored data.
- `GET /api/bands` — the raw frequency-band breakdown (including bands with
  no individually listed pairs).
- `POST /api/analyze` — body `{"numbers": [7,14,28,42,45], "use_fresh": false}`
  — returns generated duplets, matches, and unmatched pairs.
