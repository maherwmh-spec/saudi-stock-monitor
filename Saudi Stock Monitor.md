# Saudi Stock Monitor

A web application for monitoring Saudi stock market (Tadawul) with technical analysis.

## Features

- Real-time TASI index tracking
- 9 technical indicators analysis
- Buy signals detection
- Sector indices calculation
- Beautiful responsive UI

## Data Source

- **Yahoo Finance** - Free and reliable data source
- TASI Index (^TASI.SR)
- Saudi stocks data

## Deploy on Render

1. Fork this repository
2. Go to [Render.com](https://render.com)
3. Create new Web Service
4. Connect your GitHub repository
5. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:10000

## Tech Stack

- Backend: Flask + Python
- Frontend: HTML + CSS + JavaScript
- Data: Yahoo Finance API (yfinance)
- Deployment: Render.com

## License

For personal use only.

## Disclaimer

This is a technical analysis tool only, not investment advice.
