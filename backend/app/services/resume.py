"""Resume text extraction, offline heuristics and Gemini analysis."""
import io
import logging
import re
import statistics

from app.services import gemini, skills
from app.services.gemini import clamp_int, str_list

log = logging.getLogger("interviewmate.resume")

ALLOWED = {".pdf", ".docx", ".txt", ".md"}
BUZZ = ["results-driven", "results driven", "detail-oriented", "detail oriented", "dynamic", "passionate", "proven track record", "spearheaded",
        "leveraged", "leverage", "synergy", "cutting-edge", "cutting edge", "seamless", "robust", "innovative", "demonstrated ability", "adept at",
        "utilized", "utilizing", "facilitated", "orchestrated", "pivotal", "holistic", "strategic initiatives", "stakeholders", "fast-paced",
        "team player", "go-getter", "highly motivated", "self-motivated", "thrive", "comprehensive", "state-of-the-art", "streamlined", "fostered", "harnessed", "delve"]
ACTION_VERBS = ["built", "developed", "designed", "implemented", "created", "led", "improved", "reduced", "increased", "optimized", "deployed",
                "automated", "analyzed", "launched", "managed", "migrated", "integrated", "tested", "trained", "published", "won", "solved"]
SECTION_WORDS = {"summary": ["summary", "objective", "profile", "about me"], "skills": ["skills", "technical skills", "technologies"],
                 "experience": ["experience", "internship", "work history", "employment"], "projects": ["projects", "project"],
                 "education": ["education", "academic"], "certifications": ["certification", "certifications", "courses"],
                 "achievements": ["achievements", "awards", "accomplishments", "honors"]}


class ResumeError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED:
        raise ResumeError("Unsupported file type. Upload a PDF, DOCX or TXT resume.")
    if not data:
        raise ResumeError("The file is empty.")
    try:
        if ext == ".pdf":
            if not data.startswith(b"%PDF"):
                raise ResumeError("This file is not a valid PDF.")
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ResumeError("This PDF is password protected. Remove the password and upload it again.")
            text = "\n".join((page.extract_text() or "") for page in reader.pages[:8])
        elif ext == ".docx":
            if not data.startswith(b"PK"):
                raise ResumeError("This file is not a valid DOCX document.")
            import docx
            d = docx.Document(io.BytesIO(data))
            parts = [p.text for p in d.paragraphs]
            for table in d.tables:
                for row in table.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            text = "\n".join(parts)
        else:
            text = data.decode("utf-8", errors="ignore")
    except ResumeError:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("Resume parse failed: %s", exc)
        raise ResumeError("We could not read this file. Try exporting it again as a text-based PDF or DOCX.")
    text = re.sub(r"[ \t]+", " ", text.replace("\r", "")).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) < 80:
        raise ResumeError("Almost no text was found. If this is a scanned image PDF, upload a text-based PDF or DOCX instead.")
    return text[:30000]


# ------------------------------------------------------------------ offline heuristics
def _sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    marks: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        clean = re.sub(r"[^a-z ]", "", line.lower()).strip()
        if 0 < len(clean) <= 28:
            for key, words in SECTION_WORDS.items():
                if clean in words:
                    marks.append((i, key))
    out: dict[str, str] = {}
    for n, (i, key) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        out.setdefault(key, "\n".join(lines[i + 1:end]).strip())
    return out


def ai_signals(text: str) -> dict:
    """Heuristic, explainable signals. This is NOT a detector; it flags generic, buzzword-heavy writing."""
    paras = [p.strip() for p in re.split(r"\n+", text) if len(p.strip()) >= 60]
    flagged = []
    for p in paras:
        low = p.lower()
        hits = [b for b in BUZZ if b in low]
        has_number = bool(re.search(r"\d", p))
        score = 15 + 18 * len(hits) + (0 if has_number else 12) + (8 if len(p) > 180 and "," in p and not has_number else 0)
        if re.search(r"\b(and|while) (ensuring|fostering|driving|enhancing|delivering)\b", low):
            score += 10
        score = min(95, score)
        if score >= 45:
            reasons = []
            if hits:
                reasons.append("buzzwords: " + ", ".join(hits[:4]))
            if not has_number:
                reasons.append("no numbers, tools or specifics")
            flagged.append({"excerpt": p[:220], "likelihood": score, "evidence": "; ".join(reasons) or "generic phrasing"})
    flagged.sort(key=lambda f: -f["likelihood"])
    lens = [len(re.findall(r"\w+", s)) for s in re.split(r"(?<=[.!?])\s+|\n", text) if len(s.split()) > 3]
    uniform = len(lens) > 6 and statistics.pstdev(lens) < 3.5
    buzz_total = sum(text.lower().count(b) for b in BUZZ)
    density = buzz_total / max(1, len(text.split())) * 100
    percent = clamp_int(10 + density * 14 + 12 * len(flagged) / max(1, len(paras)) * 5 + (10 if uniform else 0), 3, 92)
    return {"percent": percent, "flagged": flagged[:6], "buzzword_count": buzz_total, "uniform_sentences": uniform}


def heuristic_analysis(text: str) -> dict:
    secs = _sections(text)
    found = skills.find_skills(text)
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone = re.search(r"(\+?\d[\d\s-]{8,14}\d)", text)
    links = re.findall(r"(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com)/[\w./-]+", text, re.I)
    name = next((l.strip() for l in text.splitlines() if l.strip() and "@" not in l and len(l.split()) <= 5), "")
    words = len(text.split())
    metrics = len(re.findall(r"\d+\s?%|\b\d{2,}\b|\$\s?\d|₹\s?\d", text))
    verbs = sum(1 for v in ACTION_VERBS if re.search(r"\b" + v, text, re.I))
    ai = ai_signals(text)
    scores = {
        "Contact & links": clamp_int((40 if email else 0) + (30 if phone else 0) + (30 if links else 0)),
        "Summary": 80 if "summary" in secs else 30,
        "Skills": clamp_int(min(100, len(found) * 9)),
        "Experience": 80 if "experience" in secs else 35,
        "Projects": 80 if "projects" in secs else 35,
        "Education": 85 if "education" in secs else 30,
        "Impact & metrics": clamp_int(metrics * 14 + verbs * 4),
        "Formatting & ATS": clamp_int((100 if 250 <= words <= 900 else 60) - (15 if "|" in text and text.count("|") > 30 else 0)),
    }
    overall = clamp_int(sum(scores.values()) / len(scores))
    projects = [l.strip("-•* ") for l in secs.get("projects", "").splitlines() if len(l.strip()) > 20][:5]
    weak = [k for k, v in scores.items() if v < 55]
    return {
        "candidate": {"name": name[:80], "email": email.group(0) if email else "", "phone": phone.group(0).strip() if phone else "", "location": "", "links": links[:4]},
        "summary": f"Offline analysis: {words} words, {len(found)} recognised skills, {len(secs)} standard sections found ({', '.join(secs) or 'none'}).",
        "skills": {"technical": found, "tools": [], "soft": []},
        "education": [{"degree": l.strip(), "institution": "", "year": "", "score": ""} for l in secs.get("education", "").splitlines() if l.strip()][:3],
        "experience": [{"role": l.strip(), "company": "", "duration": "", "highlights": []} for l in secs.get("experience", "").splitlines() if len(l.strip()) > 12][:4],
        "projects": [{"name": p[:80], "description": p, "technologies": [s for s in skills.find_skills(p)][:6]} for p in projects],
        "certifications": [l.strip("-•* ") for l in secs.get("certifications", "").splitlines() if l.strip()][:5],
        "achievements": [l.strip("-•* ") for l in secs.get("achievements", "").splitlines() if l.strip()][:5],
        "overall_score": overall, "verdict": "Excellent" if overall >= 85 else "Good" if overall >= 70 else "Average" if overall >= 50 else "Needs work",
        "section_scores": scores,
        "strengths": [f"{k} looks solid" for k, v in scores.items() if v >= 80][:4],
        "weaknesses": [f"{k} needs attention" for k in weak][:5],
        "suggestions": [{"section": k, "issue": "Weak or missing", "fix": "Add a clearly labelled section with specific, quantified details"} for k in weak][:5],
        "ai_generated": {"percent": ai["percent"], "confidence": "low", "sections": [{"section": "Resume text", "likelihood": f["likelihood"], "evidence": f["evidence"], "excerpt": f["excerpt"]} for f in ai["flagged"]],
                         "note": "Offline heuristic: based on buzzwords, missing specifics and uniform sentence length. It is an estimate, not proof."},
        "source": "offline",
    }


# ------------------------------------------------------------------ Gemini analysis
SYSTEM = ("You are a senior technical recruiter and resume reviewer. Extract ONLY what is literally in the resume; never invent employers, "
          "dates, skills or numbers. Use empty strings/lists for anything missing. Return ONLY valid JSON.")


def analyze(text: str) -> dict:
    base = heuristic_analysis(text)
    if not gemini.is_configured():
        return base
    prompt = f"""Analyze this resume.

RESUME TEXT:
\"\"\"
{text[:14000]}
\"\"\"

Return JSON with exactly these keys:
{{"candidate": {{"name": "", "email": "", "phone": "", "location": "", "links": []}},
 "summary": "3 sentences describing exactly what this resume contains and who the candidate is",
 "skills": {{"technical": [], "tools": [], "soft": []}},
 "education": [{{"degree": "", "institution": "", "year": "", "score": ""}}],
 "experience": [{{"role": "", "company": "", "duration": "", "highlights": []}}],
 "projects": [{{"name": "", "description": "", "technologies": []}}],
 "certifications": [], "achievements": [],
 "overall_score": 0-100 (how good the resume is for an entry-level tech job; be honest, most resumes are 45-75),
 "verdict": "Excellent|Good|Average|Needs work",
 "section_scores": {{"Contact & links": 0-100, "Summary": 0-100, "Skills": 0-100, "Experience": 0-100, "Projects": 0-100, "Education": 0-100, "Impact & metrics": 0-100, "Formatting & ATS": 0-100}},
 "strengths": [], "weaknesses": [],
 "suggestions": [{{"section": "", "issue": "", "fix": "a concrete rewrite or action"}}],
 "ai_generated": {{"percent": 0-100 estimated share of the text that reads as AI-generated,
   "confidence": "low|medium|high",
   "sections": [{{"section": "which section", "likelihood": 0-100, "evidence": "why it reads as AI-written (generic buzzwords, no specifics, uniform rhythm, unnatural polish)", "excerpt": "EXACT quote from the resume, max 200 chars"}}],
   "note": "one honest sentence about the limits of this estimate"}}}}
Give at most 6 flagged sections, only for text that really reads generic or machine-written. Genuinely specific text with tools, numbers and context should NOT be flagged."""
    try:
        r = gemini.generate_json(prompt, system=SYSTEM, temperature=0.2, max_tokens=8192)
        if not isinstance(r, dict):
            raise gemini.GeminiError("not an object")
    except (gemini.GeminiError, TypeError) as exc:
        log.warning("Gemini resume analysis failed: %s", exc)
        base["summary"] = "AI analysis was unavailable, so this is an offline analysis. " + base["summary"]
        return base

    heur = ai_signals(text)
    low_text = re.sub(r"\s+", " ", text.lower())
    flagged = []
    for s in (r.get("ai_generated") or {}).get("sections", [])[:6]:
        if not isinstance(s, dict):
            continue
        ex = str(s.get("excerpt", "")).strip()
        verified = bool(ex) and re.sub(r"\s+", " ", ex.lower())[:60] in low_text
        flagged.append({"section": str(s.get("section", ""))[:60], "likelihood": clamp_int(s.get("likelihood")), "evidence": str(s.get("evidence", ""))[:300],
                        "excerpt": ex[:220] if verified else "", "verified_excerpt": verified})
    seen = {f["excerpt"][:40] for f in flagged if f["excerpt"]}
    for f in heur["flagged"][:3]:  # add anything the local heuristic found that Gemini did not
        if f["excerpt"][:40] not in seen and len(flagged) < 8:
            flagged.append({"section": "Detected pattern", "likelihood": f["likelihood"], "evidence": f["evidence"], "excerpt": f["excerpt"], "verified_excerpt": True})
    ai_pct = clamp_int(0.65 * clamp_int((r.get("ai_generated") or {}).get("percent")) + 0.35 * heur["percent"])

    out = dict(base)
    cand = r.get("candidate") if isinstance(r.get("candidate"), dict) else {}
    out["candidate"] = {k: (cand.get(k) if k != "links" else str_list(cand.get(k), 6)) or base["candidate"].get(k, "") for k in ("name", "email", "phone", "location", "links")}
    out["summary"] = str(r.get("summary", ""))[:900] or base["summary"]
    sk = r.get("skills") if isinstance(r.get("skills"), dict) else {}
    out["skills"] = {k: str_list(sk.get(k), 40) for k in ("technical", "tools", "soft")}
    for key in ("education", "experience", "projects"):
        out[key] = [x for x in (r.get(key) or []) if isinstance(x, dict)][:8]
    out["certifications"], out["achievements"] = str_list(r.get("certifications")), str_list(r.get("achievements"))
    out["strengths"], out["weaknesses"] = str_list(r.get("strengths")), str_list(r.get("weaknesses"))
    out["suggestions"] = [{"section": str(s.get("section", "")), "issue": str(s.get("issue", "")), "fix": str(s.get("fix", ""))} for s in (r.get("suggestions") or []) if isinstance(s, dict)][:8]
    ss = r.get("section_scores") if isinstance(r.get("section_scores"), dict) else {}
    out["section_scores"] = {k: clamp_int(ss.get(k), default=base["section_scores"][k]) for k in base["section_scores"]}
    # Blend the model's holistic score with the rule-based score so one noisy answer cannot swing the result.
    out["overall_score"] = clamp_int(0.7 * clamp_int(r.get("overall_score"), default=base["overall_score"]) + 0.3 * base["overall_score"])
    s = out["overall_score"]
    out["verdict"] = "Excellent" if s >= 85 else "Good" if s >= 70 else "Average" if s >= 50 else "Needs work"
    out["ai_generated"] = {"percent": ai_pct, "confidence": str((r.get("ai_generated") or {}).get("confidence", "low")),
                           "sections": flagged, "note": str((r.get("ai_generated") or {}).get("note", "")) or "AI-writing detection is an estimate, not proof."}
    out["source"] = "gemini"
    return out
