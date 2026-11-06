# InterviewMate AI: https://interviewmate-ai-1-rlfp.onrender.com

A mock-interview and career-preparation platform: resume analysis, job matching, aptitude, technical, DSA,
coding, voice, HR and group-discussion rounds, with analytics built from your real results.

**Every module is wired to the FastAPI backend** (resume upload + analysis, job match, daily challenges, practice rounds, live coding runner, Gemini voice, group discussion, rewards and history).
See [`docs/development/checklist.md`](docs/development/checklist.md) for the status of every feature.

## Stack
Next.js 14 · React · TypeScript · Tailwind CSS · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL

## Prerequisites (Windows)
- Python 3.11+ (`python --version`)
- Node.js 18.18+ (`node --version`)
- Docker Desktop (for PostgreSQL), or a PostgreSQL install you already have

## Run it - PowerShell

### 1. Start the database
```powershell
cd InterviewMate-AI
docker compose up -d db
```

### 2. Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Open `backend\.env` and set `SECRET_KEY` to a long random value. Generate one with:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Create the tables and start the API:
```powershell
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
Check: open http://localhost:8000/api/health. You should see `{"status":"ok","database":"connected"}`.
Interactive API docs: http://localhost:8000/docs

> If PowerShell blocks `Activate.ps1`, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 3. Frontend (new PowerShell window)
```powershell
cd InterviewMate-AI\frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```
Open http://localhost:3000, create an account, and fill in your profile.

## Troubleshooting: "Cannot reach the server"
1. The backend must be running: `uvicorn app.main:app --reload --port 8000` (check http://localhost:8000/api/health).
2. The browser calls `/api/*` on the Next.js site and Next forwards it to `BACKEND_URL` (default `http://127.0.0.1:8000`), so no CORS setup is needed. Restart `npm run dev` after changing `next.config.mjs` or `.env.local`.
3. If PostgreSQL is not running, the backend now falls back to a local SQLite file and prints a warning. Start PostgreSQL (or fix `DATABASE_URL`) to use it.
4. Live voice connects straight to the backend WebSocket on port 8000 (`NEXT_PUBLIC_WS_URL` overrides it).

## Run the tests
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -v
```
Backend tests use an in-memory SQLite database, so PostgreSQL does not need to be running for them.
Frontend type-check and production build: `cd frontend; npm run build`.

## How login works (beginner explanation)
When you sign in, the backend checks your password against a **bcrypt hash** (the real password is never stored)
and sends back a signed token in an **httpOnly cookie**. JavaScript in the browser cannot read that cookie,
which protects it from many script-injection attacks. Every later request carries the cookie automatically, and
the backend uses it to find *your* user, so you can only read or change your own data.

## Project layout
```
backend/app/api         HTTP routes (auth, profile, health)
backend/app/core        settings, password hashing, tokens, rate limiting
backend/app/models      SQLAlchemy tables
backend/app/schemas     request/response validation (Pydantic)
backend/alembic         database migrations
backend/tests           pytest suite
frontend/src/app        pages (Next.js App Router)
frontend/src/lib        API client and module list
docs/                   architecture, ER diagram, development checklist
```

## Security notes
- Secrets live in git-ignored `.env` files. Only `NEXT_PUBLIC_*` values reach the browser.
- Login attempts are rate limited (in-memory; move to Redis before running multiple servers).
- In production set `COOKIE_SECURE=true`, a strong `SECRET_KEY`, and serve over HTTPS.
