import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.practice import Resume
from app.models.user import User
from app.services import gemini, skills
from app.services.gemini import clamp_int, str_list
from app.services.records import save_record

log = logging.getLogger("interviewmate.jobmatch")
router = APIRouter(prefix="/job-match", tags=["job-match"])

SYSTEM = ("You are a hiring manager comparing a candidate's resume to a job description. Base every statement on the two documents; "
          "do not invent experience the resume does not show. Return ONLY valid JSON.")


class MatchIn(BaseModel):
    job_description: str = Field(min_length=40, max_length=12000)
    job_title: str = Field(default="", max_length=120)
    resume_id: int | None = None


def _status(v) -> str:
    v = str(v).lower()
    return v if v in ("match", "partial", "missing") else "partial"


def _skill_rows(rows) -> list[dict]:
    return [{"skill": str(x.get("skill", ""))[:80], "status": _status(x.get("status")), "evidence": str(x.get("evidence", ""))[:240]}
            for x in (rows or []) if isinstance(x, dict) and x.get("skill")][:20]


@router.post("")
def match(data: MatchIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.get(Resume, data.resume_id) if data.resume_id else db.scalar(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc(), Resume.id.desc()))
    if not resume or resume.user_id != user.id:
        raise HTTPException(status_code=422, detail="Analyze your resume first. Job match compares the job description with your analyzed resume.")
    jd = data.job_description.strip()
    a = resume.analysis or {}

    # --- deterministic part: skills the JD names, and whether the resume text contains them
    jd_skills = skills.find_skills(jd)
    have = [s for s in jd_skills if skills.has_skill(resume.text, s)]
    missing = [s for s in jd_skills if s not in have]
    keyword_score = round(100 * len(have) / len(jd_skills)) if jd_skills else None

    ai: dict = {}
    if gemini.is_configured():
        prompt = f"""JOB TITLE: {data.job_title or '(not given)'}
JOB DESCRIPTION:
\"\"\"{jd}\"\"\"

CANDIDATE RESUME ANALYSIS (extracted from the uploaded resume):
{{"skills": {a.get('skills')}, "education": {a.get('education')}, "experience": {a.get('experience')}, "projects": {a.get('projects')}, "certifications": {a.get('certifications')}}}

RESUME TEXT:
\"\"\"{resume.text[:9000]}\"\"\"

Return JSON: {{"match_score": 0-100, "verdict": "Strong match|Good match|Partial match|Weak match",
"summary": "3 sentences: how well this resume fits this job and why",
"required_skills": [{{"skill": "", "status": "match|partial|missing", "evidence": "where in the resume, or why missing"}}],
"preferred_skills": [{{"skill": "", "status": "match|partial|missing", "evidence": ""}}],
"experience_fit": {{"required": "", "candidate": "", "fit": "above|meets|below|unclear"}},
"education_fit": "",
"score_breakdown": {{"skills": 0-100, "experience": 0-100, "education": 0-100, "keywords": 0-100}},
"strengths": [], "gaps": [],
"resume_improvements": [{{"section": "", "suggestion": "specific edit to tailor the resume to this job"}}],
"interview_focus": ["topics this employer will likely ask about, based on the gaps and strengths"]}}"""
        try:
            ai = gemini.generate_json(prompt, system=SYSTEM, temperature=0.2)
            if not isinstance(ai, dict):
                ai = {}
        except gemini.GeminiError as exc:
            log.warning("Gemini job match failed: %s", exc)

    if ai:
        ai_score = clamp_int(ai.get("match_score"))
        score = clamp_int(0.7 * ai_score + 0.3 * keyword_score) if keyword_score is not None else ai_score
        how = (f"70% AI comparison of your resume with the job ({ai_score}%) + 30% exact keyword overlap ({keyword_score}%)"
               if keyword_score is not None else f"AI comparison of your resume with the job ({ai_score}%); the description named no known skills to count")
    else:
        score = keyword_score if keyword_score is not None else 0
        how = "Offline estimate: share of skills named in the job description that appear in your resume"
    verdict = "Strong match" if score >= 80 else "Good match" if score >= 65 else "Partial match" if score >= 45 else "Weak match"
    bd = ai.get("score_breakdown") if isinstance(ai.get("score_breakdown"), dict) else {}
    result = {
        "score": score, "verdict": verdict, "how_calculated": how,
        "summary": str(ai.get("summary", "")) or f"{len(have)} of {len(jd_skills)} skills named in the job description appear in your resume.",
        "required_skills": _skill_rows(ai.get("required_skills")) or [{"skill": s, "status": "match" if s in have else "missing", "evidence": ""} for s in jd_skills],
        "preferred_skills": _skill_rows(ai.get("preferred_skills")),
        "experience_fit": ai.get("experience_fit") if isinstance(ai.get("experience_fit"), dict) else {},
        "education_fit": str(ai.get("education_fit", "")),
        "score_breakdown": {k: clamp_int(bd.get(k)) for k in ("skills", "experience", "education", "keywords")} if bd else
                           ({"keywords": keyword_score} if keyword_score is not None else {}),
        "keywords_found": have, "keywords_missing": missing,
        "strengths": str_list(ai.get("strengths")), "gaps": str_list(ai.get("gaps")) or [f"Add evidence of {m}" for m in missing[:6]],
        "resume_improvements": [{"section": str(x.get("section", "")), "suggestion": str(x.get("suggestion", ""))} for x in (ai.get("resume_improvements") or []) if isinstance(x, dict)][:8],
        "interview_focus": str_list(ai.get("interview_focus")), "source": "gemini" if ai else "offline",
        "resume": {"id": resume.id, "filename": resume.filename, "score": resume.score},
    }
    rec, reward = save_record(db, user.id, module="job-match", kind="job-match", topic=data.job_title or "Job match",
                              title=f"Job match: {data.job_title or 'Untitled role'}"[:200], question=jd[:1500], answer=f"Resume: {resume.filename}",
                              score=score, feedback={"verdict": verdict, "summary": result["summary"], "strengths": result["strengths"], "improvements": result["gaps"]},
                              meta={"resume_id": resume.id, "result": result})
    return {"record_id": rec.id, "result": result, "reward": reward}
