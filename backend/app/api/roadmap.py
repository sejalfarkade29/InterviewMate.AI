import copy
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import analytics
from app.api.deps import get_current_user, get_db
from app.models.practice import UserKV
from app.models.user import User
from app.services import gemini
from app.services.gemini import str_list

log = logging.getLogger("interviewmate.roadmap")
router = APIRouter(prefix="/roadmap", tags=["roadmap"])
KEY = "roadmap"


class TaskIn(BaseModel):
    id: str
    done: bool


def _load(db: Session, user_id: int) -> UserKV | None:
    return db.scalar(select(UserKV).where(UserKV.user_id == user_id, UserKV.key == KEY))


@router.get("")
def get_roadmap(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = _load(db, user.id)
    return {"roadmap": row.value if row else None}


@router.post("/generate")
def generate(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stats = analytics.build(db, user.id)
    prof = user.profile
    weak = [f"{w['topic']} ({w['module']}, {w['avg']}%)" for w in stats["weakest"]]
    modules = [f"{m['module']}: {m['avg']}% over {m['count']}" for m in stats["by_module"]]
    plan = None
    if gemini.is_configured():
        try:
            r = gemini.generate_json(f"""Create a 4-week interview preparation roadmap for a candidate.
Profile: roles {prof.preferred_roles}, skills {prof.skills}, level {prof.experience_level}, interests {prof.career_interests}.
Results so far: {modules or 'no practice yet'}. Weakest topics: {weak or 'unknown'}.
Available practice modules (use these slugs for "module"): aptitude, technical, dsa, coding, hr, voice, hr-voice, project, group-discussion, resume, job-match, daily.
Return JSON: {{"summary": "why this plan, referring to the results", "weeks": [{{"title": "Week 1: ...", "focus": "", "tasks": [{{"title": "specific task", "module": "slug"}}]}}]}}
4 weeks, 4-5 tasks each, ordered, specific (mention topics).""", temperature=0.5)
            weeks = [{"title": str(w.get("title", ""))[:100], "focus": str(w.get("focus", ""))[:200],
                      "tasks": [{"id": uuid.uuid4().hex[:8], "title": str(t.get("title", ""))[:200], "module": str(t.get("module", "daily"))[:30], "done": False}
                                for t in (w.get("tasks") or []) if isinstance(t, dict)][:6]} for w in (r.get("weeks") or []) if isinstance(w, dict)][:4]
            if weeks:
                plan = {"summary": str(r.get("summary", ""))[:600], "weeks": weeks, "source": "gemini"}
        except (gemini.GeminiError, AttributeError, TypeError) as exc:
            log.warning("Roadmap generation failed: %s", exc)
    if plan is None:
        focus = [w["topic"] for w in stats["weakest"]] or ["Aptitude basics", "Core CS fundamentals", "HR basics"]
        def t(title, module): return {"id": uuid.uuid4().hex[:8], "title": title, "module": module, "done": False}
        plan = {"summary": "Offline starter plan. It becomes more personal once you practice and add a Gemini key.", "source": "offline", "weeks": [
            {"title": "Week 1: Foundations", "focus": "Resume and baseline", "tasks": [t("Analyze your resume and fix the top 3 issues", "resume"), t("Do 5 aptitude questions", "aptitude"), t("Do one daily challenge each day", "daily")]},
            {"title": "Week 2: Technical depth", "focus": focus[0], "tasks": [t(f"Practice {focus[0]}", "technical"), t("Solve 3 DSA problems", "dsa"), t("Submit 2 coding problems", "coding")]},
            {"title": "Week 3: Communication", "focus": "HR and voice", "tasks": [t("Answer 5 most-asked HR questions", "hr"), t("Complete one voice interview", "voice"), t("Join one group discussion", "group-discussion")]},
            {"title": "Week 4: Full rehearsal", "focus": "Simulation", "tasks": [t("Run a full simulation", "simulation"), t("Review your history and retry the weakest topic", "history")]}]}
    row = _load(db, user.id) or UserKV(user_id=user.id, key=KEY, value={})
    row.value = plan
    db.add(row)
    db.commit()
    return {"roadmap": plan}


@router.put("/task")
def toggle(data: TaskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = _load(db, user.id)
    if not row:
        raise HTTPException(status_code=404, detail="Generate a roadmap first")
    plan = copy.deepcopy(row.value)
    for w in plan.get("weeks", []):
        for t in w["tasks"]:
            if t["id"] == data.id:
                t["done"] = data.done
    row.value = plan
    db.add(row)
    db.commit()
    return {"roadmap": plan}
