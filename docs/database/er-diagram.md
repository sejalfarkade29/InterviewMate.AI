# Database design (current: Phase 2)

```mermaid
erDiagram
    users ||--|| user_profiles : "has one"
    users {
        int id PK
        string email UK
        string password_hash
        bool is_active
        datetime created_at
        datetime updated_at
    }
    user_profiles {
        int id PK
        int user_id FK
        string full_name
        string education
        string college
        string degree
        string branch
        int graduation_year
        json skills
        string experience_level
        text career_interests
        json preferred_roles
    }
```

Deleting a user deletes their profile (ON DELETE CASCADE). Passwords are stored only as bcrypt hashes.
`graduation_year` has a CHECK constraint (1980-2100); `user_profiles.user_id` is unique.

## Planned relationships (added with each module)
```mermaid
erDiagram
    users ||--o{ resumes : uploads
    resumes ||--o{ resume_analysis : "analysed as"
    users ||--o{ job_descriptions : saves
    resumes ||--o{ job_matches : compared
    job_descriptions ||--o{ job_matches : compared
    users ||--o{ recruitment_processes : starts
    recruitment_processes ||--o{ interview_rounds : contains
    interview_rounds ||--o{ question_attempts : records
    question_attempts ||--o| evaluation_reports : "scored by"
    interview_rounds ||--o{ coding_submissions : records
    coding_submissions ||--o{ coding_test_results : "run against"
    interview_rounds ||--o| interview_transcripts : produces
    users ||--o{ user_progress : tracks
```
Every user-owned table will carry `user_id` and every query will filter on it.
