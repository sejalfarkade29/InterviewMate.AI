import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.practice import adaptive_level
from app.models.practice import GeneratedQuestion
from app.models.user import User
from app.services import code_analysis, code_problems, code_runner, questions
from app.services.records import save_record

router = APIRouter(prefix="/code", tags=["code"])


class RunIn(BaseModel):
    language: str
    code: str = Field(min_length=1, max_length=30000)
    stdin: str = Field(default="", max_length=20000)
    problem_id: str | None = None


class ProblemIn(BaseModel):
    topic: str = ""
    level: int | None = Field(default=None, ge=1, le=5)


class SubmitIn(BaseModel):
    problem_id: str = Field(min_length=36, max_length=36)
    language: str
    code: str = Field(min_length=1, max_length=30000)


@router.get("/languages")
def languages(user: User = Depends(get_current_user)):
    return {"available": code_runner.available_languages(), "labels": code_runner.LANGS, "starters": code_problems.STARTERS}


@router.post("/run")
def run(data: RunIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Free run: execute the code with the given input, then explain the result and estimate complexity."""
    if data.language not in code_runner.LANGS:
        raise HTTPException(status_code=422, detail="Unsupported language")
    problem = ""
    if data.problem_id:
        row = db.get(GeneratedQuestion, data.problem_id)
        if row and row.user_id == user.id:
            problem = row.payload.get("statement", "")
    result = code_runner.run_code(data.language, data.code, data.stdin)
    if result.unavailable:
        return {"run": result.to_dict(), "analysis": None}
    analysis = code_analysis.analyze(data.language, data.code, result.to_dict(), problem=problem)
    return {"run": result.to_dict(), "analysis": analysis}


@router.post("/problem")
def new_problem(data: ProblemIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    level = data.level or adaptive_level(db, user.id, "coding")
    avoid = questions.recent_questions(db, user.id, "coding", 15)
    try:
        payload = code_problems.generate(data.topic, level, avoid)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    q_id = str(uuid.uuid4())
    db.add(GeneratedQuestion(id=q_id, user_id=user.id, module="coding", kind="coding", payload=payload, created_at=datetime.now(timezone.utc).isoformat()))
    db.commit()
    public = {k: v for k, v in payload.items() if k not in ("tests", "reference_solution")}
    public["id"] = q_id
    return public


@router.post("/submit")
def submit(data: SubmitIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(GeneratedQuestion, data.problem_id)
    if not row or row.user_id != user.id or row.module != "coding":
        raise HTTPException(status_code=404, detail="Problem not found")
    if data.language not in code_runner.LANGS:
        raise HTTPException(status_code=422, detail="Unsupported language")
    p = row.payload
    results, passed, last_run = [], 0, None
    for i, t in enumerate(p["tests"]):
        r = code_runner.run_code(data.language, data.code, t["input"] + "\n")
        if r.unavailable:
            raise HTTPException(status_code=422, detail=r.unavailable)
        last_run = last_run if (last_run and last_run.get("exit_code") not in (0, None)) else r.to_dict()
        ok = (not r.timed_out and r.exit_code == 0 and code_runner.normalize(r.stdout) == code_runner.normalize(t["expected"]))
        passed += ok
        visible = i < p.get("n_visible", 2)
        results.append({"index": i + 1, "passed": ok, "hidden": not visible, "time_ms": r.duration_ms,
                        **({"input": t["input"], "expected": t["expected"], "actual": r.stdout[:500], "error": r.stderr[:500]} if visible and not ok else {}),
                        **({"error": r.stderr[:300]} if not visible and not ok and r.phase == "compile" else {})})
        if r.phase == "compile" and not ok:       # compile error: no point running every test
            for j in range(i + 1, len(p["tests"])):
                results.append({"index": j + 1, "passed": False, "hidden": j >= p.get("n_visible", 2), "time_ms": 0})
            break
    total = len(p["tests"])
    failed_visible = [{"input": r["input"], "expected": r["expected"], "actual": r["actual"]} for r in results if r.get("input") is not None and not r["passed"]]
    analysis = code_analysis.analyze(data.language, data.code, last_run or {}, problem=p["statement"],
                                     tests={"passed": passed, "total": total, "failed_visible": failed_visible})
    score = round(100 * passed / total)
    first = not row.answered
    row.answered = 1
    db.add(row)
    rec, reward = (None, None)
    if first:  # only the first submission of a problem earns XP / history, so resubmitting cannot farm rewards
        rec, reward = save_record(db, user.id, module="coding", kind="coding", topic=p.get("topic", ""), title=f"Live coding: {p['title']}",
                                  question=p["statement"], answer=data.code, score=score, question_id=row.id,
                                  feedback={"verdict": analysis["headline"], "summary": analysis["explanation"], "strengths": [f"{passed}/{total} tests passed"],
                                            "improvements": analysis["suggestions"], "extras": {"time_complexity": analysis["time_complexity"], "space_complexity": analysis["space_complexity"]}},
                                  meta={"language": data.language, "passed": passed, "total": total, "difficulty": p.get("difficulty")},
                                  extra_xp=30 if passed == total else 0)
    return {"passed": passed, "total": total, "score": score, "results": results, "analysis": analysis, "reward": reward, "record_id": rec.id if rec else None,
            "already_scored": not first}
