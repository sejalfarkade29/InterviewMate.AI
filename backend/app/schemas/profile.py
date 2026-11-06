from pydantic import BaseModel, Field, field_validator

EXPERIENCE_LEVELS = {"student", "fresher", "0-2 years", "2-5 years", "5+ years"}


def _clean_list(values: list[str]) -> list[str]:
    seen, out = set(), []
    for v in values:
        v = v.strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    education: str | None = Field(default=None, max_length=120)
    college: str | None = Field(default=None, max_length=160)
    degree: str | None = Field(default=None, max_length=120)
    branch: str | None = Field(default=None, max_length=120)
    graduation_year: int | None = Field(default=None, ge=1980, le=2100)
    skills: list[str] = Field(default_factory=list, max_length=50)
    experience_level: str | None = None
    career_interests: str | None = Field(default=None, max_length=1000)
    preferred_roles: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("skills", "preferred_roles")
    @classmethod
    def clean_lists(cls, v: list[str]) -> list[str]:
        if any(len(x) > 60 for x in v):
            raise ValueError("Each item must be 60 characters or fewer")
        return _clean_list(v)

    @field_validator("experience_level")
    @classmethod
    def valid_level(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if v not in EXPERIENCE_LEVELS:
            raise ValueError(f"Experience level must be one of: {', '.join(sorted(EXPERIENCE_LEVELS))}")
        return v


class ProfileOut(ProfileUpdate):
    email: str
    completeness: int  # percentage of profile fields filled in
