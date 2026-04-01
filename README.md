# Værbasert Turanbefaler

Flask-app som henter værdata fra yr.no, foreslår turer og viser kart/rute med Google Maps.

## Lokal kjøring

1. Installer avhengigheter:
	`pip install -r requirements.txt`
2. Opprett `.env` basert på `.env.example`.
3. Fyll inn nøkler:
	- `GROQ_API_KEY`
	- `GOOGLE_MAPS_API_KEY`
4. Start appen:
	`python app.py`

## Viktig om hosting

GitHub Pages kan bare hoste statiske filer (HTML/CSS/JS). Denne appen har Flask-backend, så den må hostes på en plattform som støtter Python-server.

## Last opp til GitHub

1. Lag et nytt repository på GitHub.
2. I prosjektmappen:
	- `git init`
	- `git add .`
	- `git commit -m "Initial commit"`
	- `git branch -M main`
	- `git remote add origin <DIN_GITHUB_REPO_URL>`
	- `git push -u origin main`

## Sikkerhet

- `.env` er ignorert i `.gitignore` og skal ikke pushes.
- Del aldri API-nøkler offentlig.