"""Prompts and helpers shared by the voice interview, HR voice interview and group discussion."""
import logging
import random

from app.services import banks, gemini
from app.services.gemini import clamp_int, str_list

log = logging.getLogger("interviewmate.interview")

STYLES = {
    "friendly": "Warm, encouraging and patient. Put the candidate at ease, acknowledge good points briefly.",
    "neutral": "Professional and neutral, like a typical corporate interviewer. Brief acknowledgements, no praise.",
    "strict": "Tough, concise and probing. Challenge vague claims, ask 'why' and 'how exactly', never accept buzzwords without evidence.",
}

PERSONAS = [
    {"name": "Arjun", "style": "assertive and confident, likes to take the lead and back points with numbers or examples", "voice": "male"},
    {"name": "Meera", "style": "analytical and structured, summarises both sides and proposes a balanced framework", "voice": "female"},
    {"name": "Kabir", "style": "a polite devil's advocate who challenges assumptions and points out risks", "voice": "male"},
]

GD_TOPICS_FALLBACK = [
    "Should AI tools be allowed in college exams?", "Work from home vs work from office: which is better for freshers?",
    "Is social media doing more harm than good to young people?", "Should coding be a compulsory subject from school level?",
    "Are startups a better first job than big companies?", "Can India become a global manufacturing hub?",
    "Is a college degree still necessary in the age of online learning?", "Should companies adopt a four-day work week?",
    "Case study: your team's product launch is delayed by 2 weeks. Cut features or delay the release?",
    "Electric vehicles: are they really the future for India?",
]


def interviewer_system(mode: str, role: str, style: str, minutes: int, resume_summary: str = "", seed_questions: list[str] | None = None) -> str:
    role = role or "Software Engineer (fresher)"
    base = (
        f"You are a human-sounding interviewer conducting a live spoken mock interview for the role: {role}. "
        f"Interviewer style: {STYLES.get(style, STYLES['neutral'])} "
        "Speak in natural, short turns (1-3 sentences), the way a real person talks. Ask exactly ONE question at a time and then stop and listen. "
        "Never read out lists, markdown or stage directions. Do not give the answer or detailed feedback during the interview. "
        "If an answer is vague, short or off-topic, ask one specific follow-up before moving on. If the candidate is silent for long, gently prompt them. "
        "If the candidate asks you to repeat or clarify, do so. If they say 'next question' or ask to move on, acknowledge in a few words and ask a NEW question. "
        f"Plan for about {minutes} minutes. Speak English. Begin now by greeting the candidate by saying you are their interviewer, and ask them to introduce themselves."
    )
    if mode == "hr":
        qs = seed_questions or [q for q, _ in random.sample(banks.HR_MOST_ASKED, 10)]
        base += (" This is an HR / behavioural round. Draw your main questions from this list of the most frequently asked real HR questions, "
                 "in roughly this order, skipping any that were already answered naturally: " + " | ".join(qs) +
                 ". Between them, ask short follow-ups using the STAR method (situation, task, action, result).")
    else:
        base += (" This is a general interview covering the candidate's background, projects, technical fundamentals for the role, and problem-solving. "
                 "Start with their introduction, then go deeper into one project, then ask 2-3 role-relevant technical questions of increasing difficulty.")
    if resume_summary:
        base += f" Candidate resume summary (use it to personalise questions, never read it back): {resume_summary[:1500]}"
    return base


def offline_reply(history: list[dict], mode: str) -> str:
    """Used by the browser-voice fallback when Gemini is unavailable."""
    asked = sum(1 for h in history if h["role"] == "ai")
    if asked == 0:
        return "Hello, I'm your interviewer today. Please start by introducing yourself."
    pool = [q for q, _ in banks.HR_MOST_ASKED] if mode == "hr" else [q["question"] for q in banks.TECH_FALLBACK]
    return random.choice(pool)


def interviewer_turn(history: list[dict], user_text: str, *, mode: str, role: str, style: str, minutes: int = 10, resume_summary: str = "") -> str:
    if not gemini.is_configured():
        return offline_reply(history, mode)
    contents = [{"role": "user" if h["role"] == "user" else "model", "parts": [{"text": h["text"]}]} for h in history[-24:]]
    system = interviewer_system(mode, role, style, minutes, resume_summary)
    prompt = user_text.strip() or "(The candidate has joined. Greet them and begin.)"
    try:
        return gemini.generate_text(prompt, system=system, history=contents, temperature=0.8, max_tokens=400).strip()
    except gemini.GeminiError as exc:
        log.warning("Interviewer turn failed: %s", exc)
        return offline_reply(history, mode)


def _transcript_text(transcript: list[dict], names: dict[str, str] | None = None) -> str:
    return "\n".join(f"{(names or {}).get(t.get('role', ''), t.get('role', '')).upper()}: {t.get('text', '').strip()}" for t in transcript if t.get("text", "").strip())[:14000]


def voice_feedback(transcript: list[dict], *, mode: str, role: str, duration_sec: int = 0) -> dict:
    user_turns = [t for t in transcript if t.get("role") == "user" and t.get("text", "").strip()]
    words = sum(len(t["text"].split()) for t in user_turns)
    if len(user_turns) == 0:
        return {"overall_score": 0, "verdict": "No answers", "summary": "No spoken answers were captured, so there is nothing to evaluate. Check your microphone and try again.",
                "scores": {}, "strengths": [], "improvements": ["Speak clearly and wait for the interviewer to finish their question"], "per_question": [], "tips": [], "source": "none"}
    if not gemini.is_configured():
        score = clamp_int(min(70, 20 + words / 4))
        return {"overall_score": score, "verdict": "Offline estimate", "summary": f"You gave {len(user_turns)} answers ({words} words). AI feedback is unavailable, so this is only a length-based estimate.",
                "scores": {}, "strengths": [], "improvements": ["Add specific examples and measurable results", "Structure answers: situation, action, result"], "per_question": [], "tips": [], "source": "offline"}
    prompt = f"""Evaluate this spoken mock interview ({'HR / behavioural' if mode == 'hr' else 'general technical'}), role: {role}.
Transcript was produced by speech recognition, so ignore small spelling errors.
{_transcript_text(transcript, {'user': 'Candidate', 'ai': 'Interviewer'})}

Return JSON: {{"overall_score": 0-100, "verdict": "Excellent|Good|Fair|Needs work", "summary": "3 sentences, speak to the candidate",
"scores": {{"communication": 0-100, "content": 0-100, "structure": 0-100, "confidence": 0-100, "relevance": 0-100}},
"strengths": [], "improvements": [specific and actionable],
"per_question": [{{"question": "", "answer_summary": "", "score": 0-100, "comment": "", "better_answer": "a stronger version in 2-3 sentences using only facts the candidate gave"}}],
"filler_words": {{"count": number of um/uh/like/basically etc., "examples": []}},
"tips": ["3 practice tips"]}}
Be honest: very short, vague or off-topic answers score low."""
    try:
        r = gemini.generate_json(prompt, system="You are an expert interview coach. Return ONLY valid JSON.", temperature=0.3, max_tokens=8192)
        sc = r.get("scores") if isinstance(r.get("scores"), dict) else {}
        return {"overall_score": clamp_int(r.get("overall_score")), "verdict": str(r.get("verdict", ""))[:30], "summary": str(r.get("summary", ""))[:800],
                "scores": {k: clamp_int(v) for k, v in sc.items()}, "strengths": str_list(r.get("strengths")), "improvements": str_list(r.get("improvements")),
                "per_question": [{"question": str(q.get("question", ""))[:300], "answer_summary": str(q.get("answer_summary", ""))[:400], "score": clamp_int(q.get("score")),
                                  "comment": str(q.get("comment", ""))[:400], "better_answer": str(q.get("better_answer", ""))[:600]} for q in (r.get("per_question") or []) if isinstance(q, dict)][:12],
                "filler_words": r.get("filler_words") if isinstance(r.get("filler_words"), dict) else {}, "tips": str_list(r.get("tips"), 5),
                "stats": {"answers": len(user_turns), "words": words, "duration_sec": duration_sec}, "source": "gemini"}
    except (gemini.GeminiError, AttributeError, TypeError) as exc:
        log.warning("Voice feedback failed: %s", exc)
        return {"overall_score": clamp_int(min(70, 20 + words / 4)), "verdict": "Offline estimate", "summary": "AI feedback could not be generated right now.",
                "scores": {}, "strengths": [], "improvements": ["Try again in a moment"], "per_question": [], "tips": [], "source": "offline"}


# ------------------------------------------------------------------ group discussion
def gd_topics(fresh: bool = True) -> list[str]:
    if gemini.is_configured() and fresh:
        try:
            r = gemini.generate_json(
                f"List 8 DIFFERENT group-discussion topics used in campus placements and hiring GD rounds (mix: current affairs, technology, business/case study, social issues, abstract). Variation seed {random.randint(1, 9999)}. "
                'Return JSON {"topics": ["..."]}. Each topic is one clear sentence or question.', temperature=1.0)
            topics = str_list(r.get("topics") if isinstance(r, dict) else r, 10)
            if len(topics) >= 4:
                return topics
        except (gemini.GeminiError, AttributeError, TypeError) as exc:
            log.warning("GD topics failed: %s", exc)
    return random.sample(GD_TOPICS_FALLBACK, 6)


def gd_turn(topic: str, transcript: list[dict], user_name: str, voice: bool, *, user_spoke: bool, elapsed_sec: int = 0) -> list[dict]:
    names = [p["name"] for p in PERSONAS]
    if not gemini.is_configured():
        pool = {"Arjun": "I think the data supports a clear direction here, and we should be decisive about it.",
                "Meera": "Let me summarise: there are benefits and risks, so a balanced framework would work best.",
                "Kabir": "I'd like to challenge that. What happens if the assumptions behind this are wrong?"}
        who = random.sample(names, 2)
        return [{"speaker": n, "text": pool[n]} for n in who]
    persona_txt = "\n".join(f"- {p['name']}: {p['style']}" for p in PERSONAS)
    limit = "Each message at most 35 words (it will be spoken aloud)." if voice else "Each message 1-3 sentences, at most 60 words."
    convo = "\n".join(f"{t['speaker']}: {t['text']}" for t in transcript[-20:]) or "(discussion has not started)"
    situation = ("The discussion is just starting. Have ONE participant open with a clear opening statement on the topic, and optionally one more participant react."
                 if not transcript else
                 f"{user_name} just spoke. Have 2 (sometimes 3) different participants respond next, in order. They must react to what {user_name} actually said (agree, build on it, politely disagree or ask a pointed question), "
                 "refer to people by name, and add NEW points rather than repeating earlier ones." if user_spoke else
                 f"{user_name} has been quiet. Have 1-2 participants continue the discussion, and one of them should invite {user_name} in by name.")
    prompt = f"""Simulate a realistic campus-placement group discussion. Topic: "{topic}".
Participants (besides the human, {user_name}):
{persona_txt}
Moderator (rarely speaks, only to redirect or keep time; elapsed {elapsed_sec // 60} min).
Conversation so far:
{convo}

{situation}
{limit} Sound like real people in a discussion: natural, occasionally disagree, no lists, no markdown.
Return JSON: {{"messages": [{{"speaker": "Arjun|Meera|Kabir|Moderator", "text": ""}}]}}"""
    try:
        r = gemini.generate_json(prompt, temperature=0.9, max_tokens=2048)
        msgs = r.get("messages") if isinstance(r, dict) else r
        out = [{"speaker": m["speaker"] if m.get("speaker") in names + ["Moderator"] else names[0], "text": str(m.get("text", "")).strip()[:500]}
               for m in (msgs or []) if isinstance(m, dict) and str(m.get("text", "")).strip()][:3]
        if out:
            return out
    except (gemini.GeminiError, AttributeError, TypeError, KeyError) as exc:
        log.warning("GD turn failed: %s", exc)
    return [{"speaker": "Meera", "text": "That's an interesting point. Could you give an example so we can compare it with the other side?"}]


def gd_feedback(topic: str, transcript: list[dict], user_name: str, duration_sec: int) -> dict:
    mine = [t for t in transcript if t.get("speaker") == user_name and t.get("text", "").strip()]
    words = sum(len(t["text"].split()) for t in mine)
    total_words = sum(len(t.get("text", "").split()) for t in transcript) or 1
    share = round(100 * words / total_words)
    stats = {"turns": len(mine), "words": words, "talk_share_percent": share, "duration_sec": duration_sec}
    if not mine:
        return {"overall_score": 0, "verdict": "No contribution", "summary": "You did not contribute to the discussion, so there is nothing to evaluate. In a real GD, speak early.",
                "scores": {}, "strengths": [], "improvements": ["Open the discussion or add your first point within the first minute", "Aim for 3-5 contributions"], "stats": stats, "source": "none"}
    if not gemini.is_configured():
        return {"overall_score": clamp_int(min(75, 25 + len(mine) * 10 + words / 8)), "verdict": "Offline estimate", "summary": f"You spoke {len(mine)} times ({words} words, {share}% of the discussion). AI feedback is unavailable.",
                "scores": {}, "strengths": [], "improvements": ["Support points with examples", "Respond to other participants by name"], "stats": stats, "source": "offline"}
    convo = "\n".join(f"{t['speaker']}: {t['text']}" for t in transcript)[:12000]
    prompt = f"""Evaluate {user_name}'s performance in this group discussion on "{topic}". Other participants are AI simulations.
{convo}

Return JSON: {{"overall_score": 0-100, "verdict": "Excellent|Good|Fair|Needs work", "summary": "3 sentences to {user_name}",
"scores": {{"content": 0-100, "communication": 0-100, "initiative": 0-100, "listening": 0-100, "leadership": 0-100, "structure": 0-100}},
"strengths": [], "improvements": [specific, quoting what they said where useful],
"best_moment": "the strongest thing they said and why", "missed_opportunity": "a moment they could have spoken or rebutted",
"model_contribution": "a sample 40-word contribution they could have made, using their own line of argument"}}
{user_name} spoke {len(mine)} times with {share}% of the words. Be honest."""
    try:
        r = gemini.generate_json(prompt, system="You are an expert GD evaluator. Return ONLY valid JSON.", temperature=0.3, max_tokens=4096)
        sc = r.get("scores") if isinstance(r.get("scores"), dict) else {}
        return {"overall_score": clamp_int(r.get("overall_score")), "verdict": str(r.get("verdict", ""))[:30], "summary": str(r.get("summary", ""))[:800],
                "scores": {k: clamp_int(v) for k, v in sc.items()}, "strengths": str_list(r.get("strengths")), "improvements": str_list(r.get("improvements")),
                "best_moment": str(r.get("best_moment", ""))[:500], "missed_opportunity": str(r.get("missed_opportunity", ""))[:500],
                "model_contribution": str(r.get("model_contribution", ""))[:500], "stats": stats, "source": "gemini"}
    except (gemini.GeminiError, AttributeError, TypeError) as exc:
        log.warning("GD feedback failed: %s", exc)
        return {"overall_score": clamp_int(min(75, 25 + len(mine) * 10 + words / 8)), "verdict": "Offline estimate", "summary": "AI feedback could not be generated right now.",
                "scores": {}, "strengths": [], "improvements": [], "stats": stats, "source": "offline"}
