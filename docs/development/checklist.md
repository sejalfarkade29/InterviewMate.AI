# Development checklist

Legend: DONE = complete and tested · PARTIAL = partly done · TODO = not started

## Phase 1 - Foundation
- DONE: .gitignore, repo layout, environment variable templates
- DONE: FastAPI app with health endpoint (checks the database connection)
- DONE: Next.js app (TypeScript, Tailwind) calling the API with cookies + CORS (verified with a live smoke test)
- DONE: README and docs
- PARTIAL: Docker. docker-compose for PostgreSQL and a backend Dockerfile exist but were NOT run in a Docker environment. No frontend Dockerfile yet.

## Phase 2 - Database
- DONE: SQLAlchemy 2 setup, Alembic configured
- DONE: Migration 0001 (`users`, `user_profiles`); upgrade, downgrade and model-sync checked on SQLite
- DONE: migration 0002 applied against the configured managed MySQL-compatible database; `0002` is the current head.
- DONE: ER diagram in `docs/database/er-diagram.md`
- DONE: `question_attempts` table added for user-owned durable history.

## Phase 3 - Frontend foundation
- DONE: landing page, responsive app layout, sidebar navigation, white professional theme, production build passes
- DONE: dashboard (real profile completeness and saved-attempt performance summary)
- DONE: working pages for every module with local Preview fallbacks, adaptive prompts, voice capture, and saved history
- TODO: toast notifications, confirmation dialogs, component tests

## Phase 4 - Authentication and profiles
- DONE: register, login, logout, protected routes (httpOnly cookie, bcrypt)
- DONE: profile view/edit with validation and completeness score
- DONE: user data isolation (tested)
- DONE: login rate limiting (single process)
- DONE: 15 backend tests passing
- TODO: password reset (needs an email provider)
- OPTIONAL: profile photo upload can be added later without changing the current profile workflow
- TODO: account settings page
- TODO: frontend automated tests; the UI was build-checked but not browser-tested

## Phases 5-18
DONE: resume analyzer, job matching, aptitude, technical interview, DSA/coding practice, browser voice mode, HR/project interviews, group discussion, simulation, analytics, roadmap, daily challenges, and searchable history. Durable user-owned attempt history is now stored in the database through /api/attempts. Provider-specific live voice and durable recordings remain separate production integrations.
