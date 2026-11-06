from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services import interview_ai
from app.services.records import save_record

router = APIRouter(prefix="/gd", tags=["group-discussion"])


class Msg(BaseModel):
    speaker: str = Field(max_length=40)
    text: str = Field(max_length=2000)


class TurnIn(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    transcript: list[Msg] = Field(default_factory=list, max_length=80)
    user_name: str = Field(default="You", max_length=40)
    voice: bool = False
    user_spoke: bool = True
    elapsed_sec: int = Field(default=0, ge=0, le=7200)


class FinishIn(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    transcript: list[Msg] = Field(max_length=120)
    user_name: str = Field(default="You", max_length=40)
    duration_sec: int = Field(default=0, ge=0, le=7200)
    voice: bool = False


@router.get("/topics")
def topics(user: User = Depends(get_current_user)):
    return {"topics": interview_ai.gd_topics(), "participants": interview_ai.PERSONAS}


@router.post("/turn")
def turn(data: TurnIn, user: User = Depends(get_current_user)):
    msgs = interview_ai.gd_turn(data.topic, [m.model_dump() for m in data.transcript], data.user_name, data.voice,
                                user_spoke=data.user_spoke, elapsed_sec=data.elapsed_sec)
    return {"messages": msgs}


@router.post("/finish")
def finish(data: FinishIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tr = [m.model_dump() for m in data.transcript]
    fb = interview_ai.gd_feedback(data.topic, tr, data.user_name, data.duration_sec)
    saved = {}
    if fb["stats"]["turns"] > 0:
        rec, reward = save_record(db, user.id, module="group-discussion", kind="voice" if data.voice else "text", topic=data.topic[:100],
                                  title=f"Group discussion: {data.topic[:80]}", question=data.topic,
                                  answer="\n".join(f"{m['speaker']}: {m['text']}" for m in tr)[:12000], score=fb["overall_score"], feedback=fb,
                                  meta={"transcript": tr, "duration_sec": data.duration_sec, "voice": data.voice})
        saved = {"record_id": rec.id, "reward": reward}
    return {"feedback": fb, **saved}
