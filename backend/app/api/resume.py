from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.practice import Resume
from app.models.user import User
from app.services import resume as svc
from app.services.records import save_record

router = APIRouter(prefix="/resume", tags=["resume"])


class PasteIn(BaseModel):
    text: str = Field(min_length=80, max_length=30000)
    name: str = Field(default="Pasted resume", max_length=120)


def _detail(r: Resume) -> dict:
    return {"id": r.id, "filename": r.filename, "score": r.score, "ai_percent": r.ai_percent, "analysis": r.analysis, "text": r.text,
            "created_at": r.created_at.isoformat() if r.created_at else None}


def _store(db: Session, user: User, filename: str, text: str) -> dict:
    analysis = svc.analyze(text)
    row = Resume(user_id=user.id, filename=filename[:255], text=text, analysis=analysis, score=analysis["overall_score"],
                 ai_percent=analysis["ai_generated"]["percent"])
    db.add(row)
    db.commit()
    db.refresh(row)
    _, reward = save_record(db, user.id, module="resume", kind="resume", title=f"Resume analysis: {filename[:60]}",
                            question=filename, answer=text[:1500], score=row.score, topic="Resume",
                            feedback={"verdict": analysis["verdict"], "summary": analysis["summary"], "strengths": analysis["strengths"],
                                      "improvements": analysis["weaknesses"], "extras": {"ai_percent": row.ai_percent}},
                            meta={"resume_id": row.id, "ai_percent": row.ai_percent})
    return {**_detail(row), "reward": reward}


@router.post("/analyze")
async def analyze_upload(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"File is too large. The limit is {settings.MAX_UPLOAD_MB} MB.")
    try:
        text = svc.extract_text(file.filename or "resume", data)
    except svc.ResumeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _store(db, user, file.filename or "resume", text)


@router.post("/analyze-text")
def analyze_text(data: PasteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _store(db, user, data.name, data.text.strip())


@router.get("")
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc(), Resume.id.desc()).limit(30)).all()
    return [{"id": r.id, "filename": r.filename, "score": r.score, "ai_percent": r.ai_percent,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


@router.get("/{resume_id}")
def get_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Resume, resume_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    return _detail(row)


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Resume, resume_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(row)
    db.commit()
