"""XP, levels, streaks and badges. Everything is derived from saved practice records."""
import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.practice import PracticeRecord, UserStats

TITLES = ["Rookie", "Learner", "Practitioner", "Candidate", "Contender", "Achiever", "Pro", "Expert", "Master", "Legend"]


def level_for_xp(xp: int) -> int:
    return int(0.5 + math.sqrt(0.25 + max(xp, 0) / 50))


def xp_for_level(level: int) -> int:
    return 50 * (level - 1) * level


def title_for_level(level: int) -> str:
    return TITLES[min(level - 1, len(TITLES) - 1)]


def level_info(xp: int) -> dict:
    level = level_for_xp(xp)
    start, end = xp_for_level(level), xp_for_level(level + 1)
    return {
        "xp": xp, "level": level, "title": title_for_level(level),
        "xp_into_level": xp - start, "xp_for_next": end - start,
        "progress": round(100 * (xp - start) / (end - start)),
    }


def xp_for(module: str, score: int, extra: int = 0) -> int:
    base = {"resume": 30, "job-match": 25, "voice": 45, "hr-voice": 45, "group-discussion": 45, "simulation": 80}.get(module, 12)
    return base + round(score * 0.4) + extra


# --- badges ---------------------------------------------------------------
BADGES = [
    ("first-step", "First step", "Complete your first activity", lambda s: s["total"] >= 1, lambda s: (s["total"], 1)),
    ("resume-ready", "Resume ready", "Analyze a resume", lambda s: s["by_module"].get("resume", 0) >= 1, lambda s: (s["by_module"].get("resume", 0), 1)),
    ("job-hunter", "Job hunter", "Run a job match", lambda s: s["by_module"].get("job-match", 0) >= 1, lambda s: (s["by_module"].get("job-match", 0), 1)),
    ("daily-habit", "Daily habit", "Reach a 3-day streak", lambda s: s["best_streak"] >= 3, lambda s: (s["best_streak"], 3)),
    ("week-warrior", "Week warrior", "Reach a 7-day streak", lambda s: s["best_streak"] >= 7, lambda s: (s["best_streak"], 7)),
    ("aptitude-ace", "Aptitude ace", "Score 80+ on 5 aptitude questions", lambda s: s["high_aptitude"] >= 5, lambda s: (s["high_aptitude"], 5)),
    ("code-runner", "Code submitter", "Submit 3 coding solutions", lambda s: s["by_module"].get("coding", 0) >= 3, lambda s: (s["by_module"].get("coding", 0), 3)),
    ("voice-confident", "Voice confident", "Finish a voice interview", lambda s: s["by_module"].get("voice", 0) + s["by_module"].get("hr-voice", 0) >= 1, lambda s: (s["by_module"].get("voice", 0) + s["by_module"].get("hr-voice", 0), 1)),
    ("team-player", "Team player", "Finish a group discussion", lambda s: s["by_module"].get("group-discussion", 0) >= 1, lambda s: (s["by_module"].get("group-discussion", 0), 1)),
    ("hr-ready", "HR ready", "Answer 5 HR questions", lambda s: s["by_module"].get("hr", 0) >= 5, lambda s: (s["by_module"].get("hr", 0), 5)),
    ("perfectionist", "Perfectionist", "Score 95+ on any answer", lambda s: s["best_score"] >= 95, lambda s: (s["best_score"], 95)),
    ("centurion", "Centurion", "Complete 100 activities", lambda s: s["total"] >= 100, lambda s: (s["total"], 100)),
    ("level-5", "Level 5", "Reach level 5", lambda s: s["level"] >= 5, lambda s: (s["level"], 5)),
    ("level-10", "Level 10", "Reach level 10", lambda s: s["level"] >= 10, lambda s: (s["level"], 10)),
]


def _summary(db: Session, user_id: int, stats: UserStats) -> dict:
    rows = db.execute(select(PracticeRecord.module, func.count(), func.max(PracticeRecord.score)).where(PracticeRecord.user_id == user_id).group_by(PracticeRecord.module)).all()
    by_module = {m: c for m, c, _ in rows}
    high_aptitude = db.scalar(select(func.count()).select_from(PracticeRecord).where(
        PracticeRecord.user_id == user_id, PracticeRecord.module == "aptitude", PracticeRecord.score >= 80)) or 0
    best = max([b or 0 for *_, b in rows], default=0)
    return {"total": sum(by_module.values()), "by_module": by_module, "high_aptitude": high_aptitude,
            "best_score": best, "best_streak": stats.best_streak, "level": level_for_xp(stats.xp)}


def badge_state(db: Session, user_id: int, stats: UserStats) -> list[dict]:
    s = _summary(db, user_id, stats)
    out = []
    for bid, name, desc, test, prog in BADGES:
        have, need = prog(s)
        out.append({"id": bid, "name": name, "description": desc, "earned": bool(test(s)), "progress": min(have, need), "target": need})
    return out


def get_stats(db: Session, user_id: int) -> UserStats:
    stats = db.get(UserStats, user_id)
    if stats is None:
        stats = UserStats(user_id=user_id, xp=0, streak=0, best_streak=0)
        db.add(stats)
        db.flush()
    return stats


def _touch_streak(stats: UserStats, today: date) -> None:
    if stats.last_active == today:
        return
    stats.streak = stats.streak + 1 if stats.last_active == today - timedelta(days=1) else 1
    stats.best_streak = max(stats.best_streak, stats.streak)
    stats.last_active = today


def before_state(db: Session, user_id: int) -> dict:
    """Snapshot taken BEFORE a new record is added, so level-ups and new badges can be detected."""
    stats = get_stats(db, user_id)
    return {"level": level_for_xp(stats.xp), "badges": {b["id"] for b in badge_state(db, user_id, stats) if b["earned"]}}


def award(db: Session, user_id: int, xp: int, before: dict) -> dict:
    """Add XP, update the streak and report level-ups and new badges (call after the record is flushed)."""
    stats = get_stats(db, user_id)
    before_level, before_badges = before["level"], before["badges"]
    stats.xp += xp
    _touch_streak(stats, datetime.now(timezone.utc).date())
    db.flush()
    after = level_info(stats.xp)
    new_badges = [b for b in badge_state(db, user_id, stats) if b["earned"] and b["id"] not in before_badges]
    return {"xp_gained": xp, **after, "level_up": after["level"] > before_level, "previous_level": before_level,
            "streak": stats.streak, "new_badges": new_badges}


def overview(db: Session, user_id: int) -> dict:
    stats = get_stats(db, user_id)
    recs = db.scalars(select(PracticeRecord).where(PracticeRecord.user_id == user_id).order_by(PracticeRecord.created_at, PracticeRecord.id)).all()
    # Replay XP to find when each level was reached.
    timeline, running, level = [{"level": 1, "title": title_for_level(1), "reached_at": None, "xp": 0}], 0, 1
    for r in recs:
        running += r.xp
        new_level = level_for_xp(running)
        while level < new_level:
            level += 1
            timeline.append({"level": level, "title": title_for_level(level), "reached_at": r.created_at.isoformat() if r.created_at else None, "xp": xp_for_level(level)})
    today = datetime.now(timezone.utc).date()
    week = {(today - timedelta(days=i)).isoformat(): 0 for i in range(6, -1, -1)}
    for r in recs:
        d = r.created_at.date().isoformat() if r.created_at else None
        if d in week:
            week[d] += r.xp
    streak = stats.streak if stats.last_active and stats.last_active >= today - timedelta(days=1) else 0
    return {
        **level_info(stats.xp), "streak": streak, "best_streak": stats.best_streak,
        "badges": badge_state(db, user_id, stats), "timeline": timeline,
        "weekly_xp": [{"date": d, "xp": v} for d, v in week.items()],
        "recent": [{"id": r.id, "title": r.title, "module": r.module, "xp": r.xp, "score": r.score,
                    "created_at": r.created_at.isoformat() if r.created_at else None} for r in reversed(recs[-10:])],
        "total_activities": len(recs),
    }
