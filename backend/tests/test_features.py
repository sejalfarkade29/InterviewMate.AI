import io
import json

from tests.conftest import register

RESUME = """Sejal Farkade
sejal@example.com | +91 98765 43210 | github.com/sejal

Summary
Computer science student building web apps.

Skills
Python, SQL, React, FastAPI, Git, Docker

Projects
InterviewMate - built a FastAPI and React interview platform used by 120 students, reduced answer review time by 40%.
Weather App - React and REST API project.

Education
B.Tech Computer Science, 2026, CGPA 8.4

Experience
Intern at Acme - developed REST endpoints in Python and wrote pytest tests, improved coverage to 85%.
"""


def upload(client, name="resume.txt", data=RESUME.encode(), mime="text/plain"):
    return client.post("/api/resume/analyze", files={"file": (name, io.BytesIO(data), mime)})


# ---------------------------------------------------------------- resume
def test_resume_upload_txt_offline(client):
    register(client)
    r = upload(client)
    assert r.status_code == 200, r.text
    body = r.json()
    a = body["analysis"]
    assert a["candidate"]["email"] == "sejal@example.com"
    assert "python" in a["skills"]["technical"] and "react" in a["skills"]["technical"]
    assert 0 <= body["score"] <= 100 and 0 <= body["ai_percent"] <= 100
    assert "Sejal" in body["text"]
    assert body["reward"]["xp_gained"] > 0
    assert client.get("/api/resume").json()[0]["filename"] == "resume.txt"


def test_resume_upload_docx_and_pdf(client):
    register(client)
    import docx
    d = docx.Document()
    for line in RESUME.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    assert upload(client, "r.docx", buf.getvalue()).json()["analysis"]["candidate"]["email"] == "sejal@example.com"
    lines = [l for l in RESUME.splitlines() if l.strip()]
    stream = "BT /F1 10 Tf 40 780 Td 12 TL " + " ".join(f"({l.replace('(', '').replace(')', '')}) Tj T*" for l in lines) + " ET"
    objs = ["<</Type/Catalog/Pages 2 0 R>>", "<</Type/Pages/Kids[3 0 R]/Count 1>>",
            "<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
            f"<</Length {len(stream)}>>\nstream\n{stream}\nendstream", "<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    body, offsets = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(body))
        body += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(body)
    body += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    pdf = (body + f"trailer\n<</Root 1 0 R/Size {len(objs) + 1}>>\nstartxref\n{xref}\n%%EOF").encode()
    r = upload(client, "r.pdf", pdf, "application/pdf")
    assert r.status_code == 200, r.text
    assert "python" in r.json()["analysis"]["skills"]["technical"]


def test_resume_upload_validation(client):
    register(client)
    assert upload(client, "r.exe", b"MZ....").status_code == 422
    assert upload(client, "r.pdf", b"not a pdf").status_code == 422
    assert upload(client, "r.txt", b"").status_code == 422
    assert upload(client, "r.txt", b"too short").status_code == 422
    assert upload(client, "r.txt", b"x" * (6 * 1024 * 1024)).status_code == 413


def test_resume_requires_auth_and_is_private(client):
    assert upload(client).status_code == 401
    register(client, email="a@example.com")
    rid = upload(client).json()["id"]
    client.cookies.clear()
    register(client, email="b@example.com")
    assert client.get(f"/api/resume/{rid}").status_code == 404
    assert client.get("/api/resume").json() == []


def test_resume_gemini_analysis_flags_only_verified_excerpts(client, fake_gemini):
    register(client)
    fake_gemini["responder"] = lambda p, s: json.dumps({
        "candidate": {"name": "Sejal Farkade", "email": "sejal@example.com"}, "summary": "A CS student.",
        "skills": {"technical": ["Python"], "tools": [], "soft": []}, "overall_score": 80, "verdict": "Good",
        "section_scores": {"Skills": 90}, "strengths": ["Metrics"], "weaknesses": [], "suggestions": [],
        "ai_generated": {"percent": 50, "confidence": "medium", "note": "estimate", "sections": [
            {"section": "Summary", "likelihood": 70, "evidence": "generic", "excerpt": "Computer science student building web apps."},
            {"section": "Made up", "likelihood": 90, "evidence": "x", "excerpt": "this text is not in the resume at all"}]}})
    body = upload(client).json()
    secs = body["analysis"]["ai_generated"]["sections"]
    assert body["analysis"]["source"] == "gemini"
    assert any(s["excerpt"].startswith("Computer science student") for s in secs)
    assert all(s["excerpt"] == "" for s in secs if s["section"] == "Made up")
    assert 0 <= body["ai_percent"] <= 100


# ---------------------------------------------------------------- job match
JD = "We need a Python developer with FastAPI, SQL and Docker experience. Kubernetes and AWS are a plus. Good communication skills required."


def test_job_match_requires_resume_then_uses_it(client):
    register(client)
    assert client.post("/api/job-match", json={"job_description": JD}).status_code == 422
    upload(client)
    r = client.post("/api/job-match", json={"job_description": JD, "job_title": "Backend Dev"})
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert "python" in res["keywords_found"] and "fastapi" in res["keywords_found"]
    assert "kubernetes" in res["keywords_missing"] and "aws" in res["keywords_missing"]
    assert 0 < res["score"] < 100 and res["resume"]["filename"] == "resume.txt"


def test_job_match_blends_ai_and_keyword_score(client, fake_gemini):
    register(client)
    upload(client)
    fake_gemini["responder"] = lambda p, s: json.dumps({"match_score": 90, "summary": "Strong", "required_skills": [{"skill": "Python", "status": "match", "evidence": "Skills"}]})
    res = client.post("/api/job-match", json={"job_description": JD}).json()["result"]
    kw = round(100 * len(res["keywords_found"]) / (len(res["keywords_found"]) + len(res["keywords_missing"])))
    assert res["score"] == round(0.7 * 90 + 0.3 * kw)
    assert "70%" in res["how_calculated"]


# ---------------------------------------------------------------- practice / daily / rewards / history
def ask(client, module="aptitude", **kw):
    r = client.post("/api/practice/question", json={"module": module, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_aptitude_question_hides_answer_and_scores_server_side(client):
    register(client)
    q = ask(client)
    assert q["type"] == "mcq" and len(q["options"]) == 4
    assert "answer_index" not in q and "explanation" not in q
    from app.services.banks import APTITUDE_FALLBACK
    correct = next(p["answer_index"] for p in APTITUDE_FALLBACK if p["question"] == q["question"])
    ok = client.post("/api/practice/answer", json={"question_id": q["id"], "choice": correct}).json()
    assert ok["result"]["score"] == 100 and ok["result"]["correct"] and ok["reward"]["xp_gained"] > 0
    assert client.post("/api/practice/answer", json={"question_id": q["id"], "choice": correct}).status_code == 409
    q2 = ask(client)
    bad = client.post("/api/practice/answer", json={"question_id": q2["id"], "choice": (next(p["answer_index"] for p in APTITUDE_FALLBACK if p["question"] == q2["question"]) + 1) % 4}).json()
    assert bad["result"]["score"] == 0 and bad["result"]["ideal_answer"]


def test_question_cannot_be_answered_by_another_user(client):
    register(client, email="a@example.com")
    q = ask(client)
    client.cookies.clear()
    register(client, email="b@example.com")
    assert client.post("/api/practice/answer", json={"question_id": q["id"], "choice": 0}).status_code == 404


def test_text_answer_offline_and_next_question_is_new(client):
    register(client)
    seen = set()
    for _ in range(5):
        q = ask(client, "technical")
        assert q["question"] not in seen
        seen.add(q["question"])
        r = client.post("/api/practice/answer", json={"question_id": q["id"], "answer": "A process has its own memory while a thread shares memory, so threads are lighter and need synchronisation."})
        assert r.status_code == 200 and 0 <= r.json()["result"]["score"] <= 100
    assert client.post("/api/practice/answer", json={"question_id": q["id"], "answer": "x"}).status_code in (409, 422)


def test_hr_asks_most_frequent_real_questions(client):
    register(client)
    from app.services.banks import HR_MOST_ASKED
    bank = {q for q, _ in HR_MOST_ASKED}
    qs = [ask(client, "hr")["question"] for _ in range(6)]
    assert all(q in bank for q in qs) and len(set(qs)) == 6


def test_project_questions_need_resume(client):
    register(client)
    assert client.post("/api/practice/question", json={"module": "project"}).status_code == 422
    upload(client)
    assert client.post("/api/practice/question", json={"module": "project"}).status_code == 200


def test_daily_rotates_question_types(client):
    register(client)
    kinds = []
    for _ in range(4):
        q = client.post("/api/daily/question", json={}).json()
        kinds.append(q["kind"])
    assert len(set(kinds)) == 4, kinds
    assert client.get("/api/daily/status").json()["completed_today"] == 0


def test_rewards_levels_badges_and_history(client):
    register(client)
    r0 = client.get("/api/rewards").json()
    assert r0["level"] == 1 and r0["xp"] == 0 and not any(b["earned"] for b in r0["badges"])
    from app.services.banks import APTITUDE_FALLBACK
    level_ups, new_badges = 0, []
    for _ in range(12):
        q = ask(client)
        correct = next(p["answer_index"] for p in APTITUDE_FALLBACK if p["question"] == q["question"])
        rw = client.post("/api/practice/answer", json={"question_id": q["id"], "choice": correct}).json()["reward"]
        level_ups += rw["level_up"]
        new_badges += [b["id"] for b in rw["new_badges"]]
    r = client.get("/api/rewards").json()
    assert r["xp"] > 100 and r["level"] >= 2 and level_ups >= 1
    assert "first-step" in new_badges and any(b["id"] == "first-step" and b["earned"] for b in r["badges"])
    assert r["streak"] == 1 and len(r["timeline"]) == r["level"] and len(r["weekly_xp"]) == 7 and r["recent"]
    h = client.get("/api/history").json()
    assert h["total"] == 12 and h["items"][0]["module"] == "aptitude"
    one = client.get(f"/api/history/{h['items'][0]['id']}").json()
    assert one["question"] and one["answer"] and one["feedback"]["score"] == 100
    assert client.get("/api/history", params={"q": "zzzzqqq"}).json()["total"] == 0
    assert client.get("/api/history", params={"module": "hr"}).json()["total"] == 0
    assert client.delete(f"/api/history/{one['id']}").status_code == 204
    assert client.get("/api/history").json()["total"] == 11
    assert client.delete("/api/history").status_code == 204
    assert client.get("/api/history").json()["total"] == 0
    assert client.get("/api/analytics").json()["total"] == 0


def test_history_is_private(client):
    register(client, email="a@example.com")
    q = ask(client)
    client.post("/api/practice/answer", json={"question_id": q["id"], "choice": 0})
    rid = client.get("/api/history").json()["items"][0]["id"]
    client.cookies.clear()
    register(client, email="b@example.com")
    assert client.get(f"/api/history/{rid}").status_code == 404
    assert client.delete(f"/api/history/{rid}").status_code == 404
    assert client.get("/api/history").json()["total"] == 0


def test_gemini_generated_question_and_evaluation(client, fake_gemini):
    register(client)

    def responder(prompt, system):
        if "Candidate answer" in prompt:
            return json.dumps({"score": 82, "verdict": "Good", "summary": "Solid.", "strengths": ["Clear"], "improvements": ["Add example"], "ideal_answer": "Model", "rubric": {"clarity": 80}})
        return json.dumps({"topic": "Python", "difficulty": 2, "question": "Explain Python's GIL and one way around it.", "hints": ["threads"], "keywords": ["gil"], "ideal_points": ["one thread at a time"]})
    fake_gemini["responder"] = responder
    q = ask(client, "technical")
    assert q["question"].startswith("Explain Python's GIL") and q["source"] == "gemini"
    res = client.post("/api/practice/answer", json={"question_id": q["id"], "answer": "The GIL lets one thread run Python bytecode at a time; use multiprocessing."}).json()
    assert res["result"]["score"] == 82 and res["result"]["source"] == "gemini"


def test_gemini_failure_falls_back_instead_of_erroring(client, fake_gemini):
    register(client)
    from app.services.gemini import GeminiError

    def boom(prompt, system):
        raise GeminiError("down")
    fake_gemini["responder"] = boom
    q = ask(client, "technical")
    assert q["source"] == "offline"
    r = client.post("/api/practice/answer", json={"question_id": q["id"], "answer": "Threads share memory and processes do not, so threads are cheaper."})
    assert r.status_code == 200 and r.json()["result"]["source"] == "offline"


# ---------------------------------------------------------------- code
def test_code_run_success_error_and_timeout(client):
    register(client)
    ok = client.post("/api/code/run", json={"language": "python", "code": "n=int(input())\nprint(sum(range(n)))", "stdin": "5"}).json()
    assert ok["run"]["stdout"].strip() == "10" and ok["run"]["exit_code"] == 0
    assert ok["analysis"]["verdict"] == "works" and ok["analysis"]["time_complexity"] and ok["analysis"]["space_complexity"]
    err = client.post("/api/code/run", json={"language": "python", "code": "print(1/0)"}).json()
    assert err["analysis"]["verdict"] == "error" and "ZeroDivisionError" in err["run"]["stderr"] and err["analysis"]["errors"][0]["line"] == 1
    syn = client.post("/api/code/run", json={"language": "python", "code": "def f(:\n  pass"}).json()
    assert syn["analysis"]["verdict"] == "error"
    from app.core.config import settings
    settings.CODE_RUN_TIMEOUT_SECONDS, old = 1, settings.CODE_RUN_TIMEOUT_SECONDS
    try:
        slow = client.post("/api/code/run", json={"language": "python", "code": "while True: pass"}).json()
    finally:
        settings.CODE_RUN_TIMEOUT_SECONDS = old
    assert slow["run"]["timed_out"] and slow["analysis"]["verdict"] == "error"


def test_code_complexity_heuristic_detects_nested_loops(client):
    register(client)
    code = "n=int(input())\nc=0\nfor i in range(n):\n    for j in range(n):\n        c+=1\nprint(c)"
    a = client.post("/api/code/run", json={"language": "python", "code": code, "stdin": "3"}).json()["analysis"]
    assert a["time_complexity"] == "O(n^2)"


def test_code_run_javascript_and_cpp_if_installed(client):
    register(client)
    langs = client.get("/api/code/languages").json()["available"]
    if langs["javascript"]:
        r = client.post("/api/code/run", json={"language": "javascript", "code": "console.log(2+3)"}).json()
        assert r["run"]["stdout"].strip() == "5"
    if langs["cpp"]:
        r = client.post("/api/code/run", json={"language": "cpp", "code": "#include <iostream>\nint main(){std::cout<<7;}"}).json()
        assert r["run"]["stdout"].strip() == "7"
        bad = client.post("/api/code/run", json={"language": "cpp", "code": "int main(){ return x; }"}).json()
        assert bad["run"]["phase"] == "compile" and bad["analysis"]["verdict"] == "error"


def test_code_problem_submit_flow(client):
    register(client)
    p = client.post("/api/code/problem", json={}).json()
    assert p["title"] and p["examples"] and "tests" not in p and "reference_solution" not in p
    from app.services.code_problems import FALLBACK
    spec = next(f for f in FALLBACK if f["title"] == p["title"])
    wrong = client.post("/api/code/submit", json={"problem_id": p["id"], "language": "python", "code": "print('nope')"}).json()
    assert wrong["passed"] < wrong["total"] and wrong["analysis"]["verdict"] in ("incorrect",)
    assert any(r["hidden"] for r in wrong["results"]) and all("expected" not in r for r in wrong["results"] if r["hidden"])
    good = client.post("/api/code/submit", json={"problem_id": p["id"], "language": "python", "code": spec["reference"]}).json()
    assert good["passed"] == good["total"] and good["analysis"]["verdict"] == "correct"
    # The first submission is what earns XP and history; resubmitting cannot farm rewards.
    assert wrong["reward"]["xp_gained"] > 0 and good["reward"] is None and good["already_scored"]
    assert client.get("/api/history", params={"module": "coding"}).json()["total"] == 1


def test_code_requires_auth(client):
    assert client.post("/api/code/run", json={"language": "python", "code": "print(1)"}).status_code == 401


# ---------------------------------------------------------------- group discussion, voice fallback, simulation, roadmap
def test_group_discussion_flow_offline(client):
    register(client, name="Sejal F")
    t = client.get("/api/gd/topics").json()
    assert len(t["topics"]) >= 4 and {p["name"] for p in t["participants"]} == {"Arjun", "Meera", "Kabir"}
    topic = t["topics"][0]
    first = client.post("/api/gd/turn", json={"topic": topic, "transcript": [], "user_name": "Sejal"}).json()["messages"]
    assert first and all(m["speaker"] in ("Arjun", "Meera", "Kabir", "Moderator") for m in first)
    tr = [*first, {"speaker": "Sejal", "text": "I believe a balanced approach works because it protects quality while keeping speed."}]
    nxt = client.post("/api/gd/turn", json={"topic": topic, "transcript": tr, "user_name": "Sejal"}).json()["messages"]
    assert nxt
    fin = client.post("/api/gd/finish", json={"topic": topic, "transcript": tr + nxt, "user_name": "Sejal", "duration_sec": 120}).json()
    assert fin["feedback"]["stats"]["turns"] == 1 and fin["reward"]["xp_gained"] > 0
    silent = client.post("/api/gd/finish", json={"topic": topic, "transcript": first, "user_name": "Sejal"}).json()
    assert silent["feedback"]["overall_score"] == 0 and "reward" not in silent


def test_voice_browser_fallback_and_feedback(client):
    register(client)
    r = client.post("/api/voice/turn", json={"mode": "hr", "history": [], "user_text": ""}).json()
    assert r["reply"]
    tr = [{"role": "ai", "text": "Tell me about yourself."}, {"role": "user", "text": "I am a final year student who built a FastAPI project and I enjoy solving problems with data."}]
    fb = client.post("/api/voice/feedback", json={"mode": "hr", "role": "Dev", "transcript": tr, "duration_sec": 60}).json()
    assert fb["feedback"]["overall_score"] > 0 and fb["reward"]["xp_gained"] > 0
    assert client.get("/api/history", params={"module": "hr-voice"}).json()["total"] == 1


def test_simulation_report_uses_own_records(client):
    register(client)
    ids = []
    for module in ("aptitude", "technical"):
        q = ask(client, module if module != "aptitude" else "simulation", kind="aptitude" if module == "aptitude" else "technical")
        body = {"question_id": q["id"], **({"choice": 0} if q["type"] == "mcq" else {"answer": "threads share memory but processes do not"})}
        ids.append(client.post("/api/practice/answer", json=body).json()["record_id"])
    rep = client.post("/api/simulation/report", json={"role": "Dev", "record_ids": ids}).json()
    assert rep["report"]["per_round"] and rep["reward"]["xp_gained"] > 40
    client.cookies.clear()
    register(client, email="other@example.com")
    assert client.post("/api/simulation/report", json={"role": "Dev", "record_ids": ids}).status_code == 404


def test_roadmap_generate_and_toggle(client):
    register(client)
    assert client.get("/api/roadmap").json()["roadmap"] is None
    plan = client.post("/api/roadmap/generate").json()["roadmap"]
    task = plan["weeks"][0]["tasks"][0]
    out = client.put("/api/roadmap/task", json={"id": task["id"], "done": True}).json()["roadmap"]
    assert out["weeks"][0]["tasks"][0]["done"] is True and client.get("/api/roadmap").json()["roadmap"]["weeks"][0]["tasks"][0]["done"]


def test_health_reports_database_and_gemini(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["gemini_configured"] is False


def test_cors_allows_127_and_localhost(client):
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"):
        r = client.options("/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
        assert r.headers.get("access-control-allow-origin") == origin
