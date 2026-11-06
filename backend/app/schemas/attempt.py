from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

class AttemptCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    module: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    score: int = Field(ge=0, le=10000)
    maxScore: int = Field(default=100, ge=1, le=10000)
    summary: str = Field(min_length=1, max_length=2000)
    details: list[str] = Field(default_factory=list, max_length=50)
    questionId: str | None = Field(default=None, max_length=120)
    level: int | None = Field(default=None, ge=1, le=5)
    sourceUrl: HttpUrl | None = None

class AttemptOut(BaseModel):
    id: str
    module: str
    title: str
    score: int
    maxScore: int
    createdAt: datetime
    summary: str
    details: list[str]
    questionId: str | None = None
    level: int | None = None
    sourceUrl: str | None = None
