# Architecture

```
Browser (Next.js :3000) --fetch + httpOnly cookie--> FastAPI (:8000) --SQLAlchemy--> PostgreSQL (:5432)
                                                          |
                                          (later) Gemini API / Gemini Live, code sandbox
```

- Frontend renders pages and calls `/api/*`. It never holds secrets.
- Backend owns validation, authentication, business logic and all AI calls (API keys stay server-side).
- Database is the single source of truth; every analytics number will be a query over saved attempts.
- Deterministic vs AI: scoring, analytics and code execution use plain code/SQL; AI is reserved for
  open-ended feedback and question generation, with schema validation of its output.
