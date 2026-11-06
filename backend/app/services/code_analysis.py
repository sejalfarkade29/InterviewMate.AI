"""Explains run results and estimates time/space complexity (Gemini first, local heuristics second)."""
import ast
import logging
import re

from app.services import gemini
from app.services.gemini import clamp_int, str_list

log = logging.getLogger("interviewmate.code")

SYSTEM = ("You are a precise code reviewer in a coding interview. Use the ACTUAL program output and errors you are given; do not guess "
          "outputs. Complexity must be justified in terms of the input size n. Return ONLY valid JSON.")


def _py_depth(tree: ast.AST) -> tuple[int, bool, bool]:
    best, recursion, sorting = 0, False, False
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    def walk(node, depth):
        nonlocal best, recursion, sorting
        for child in ast.iter_child_nodes(node):
            d = depth + 1 if isinstance(child, (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) else depth
            best = max(best, d)
            if isinstance(child, ast.Call):
                f = child.func
                nm = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
                if nm in ("sorted", "sort"):
                    sorting = True
            walk(child, d)
    walk(tree, 0)
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == fn.name and fn.name in names:
                recursion = True
    return best, recursion, sorting


def heuristic_complexity(language: str, code: str) -> tuple[str, str, str]:
    depth, recursion, sorting = 0, False, False
    if language == "python":
        try:
            depth, recursion, sorting = _py_depth(ast.parse(code))
        except SyntaxError:
            pass
    else:
        # brace languages: estimate nesting from indentation of loop headers
        stack: list[int] = []
        for line in code.splitlines():
            if not line.strip() or line.strip().startswith(("}", "//", "#")):
                continue
            indent = len(line) - len(line.lstrip())
            while stack and indent <= stack[-1]:
                stack.pop()
            if re.search(r"\b(for|while)\b\s*\(", line):
                stack.append(indent)
                depth = max(depth, len(stack))
        sorting = bool(re.search(r"\bsort\(|Arrays\.sort|Collections\.sort", code))
        recursion = False
    time = "O(1)" if depth == 0 and not sorting and not recursion else "O(n)" if depth == 1 else f"O(n^{depth})" if depth > 1 else "O(n log n)" if sorting else "O(2^n) or O(n) (recursive)"
    if sorting and depth <= 1:
        time = "O(n log n)"
    space = "O(n)" if re.search(r"\[\]|\{\}|dict\(|list\(|set\(|new\s+\w+\[|vector<|ArrayList|HashMap|HashSet", code) else "O(1)"
    return time, space, "Estimated from loop nesting and data structures (offline heuristic)."


def _last_error_line(stderr: str) -> str:
    lines = [l for l in stderr.strip().splitlines() if l.strip()]
    return lines[-1] if lines else ""


def _line_number(stderr: str) -> int | None:
    m = re.findall(r'line (\d+)', stderr) or re.findall(r":(\d+):\d*:? error", stderr) or re.findall(r"\.java:(\d+)", stderr) or re.findall(r"\.js:(\d+)", stderr)
    return int(m[-1]) if m else None


def analyze(language: str, code: str, run: dict, *, problem: str = "", tests: dict | None = None) -> dict:
    failed = bool(run.get("timed_out")) or run.get("phase") == "compile" or (run.get("exit_code") not in (0, None))
    t, s, note = heuristic_complexity(language, code)
    base_verdict = "error" if failed else "works"
    if tests:
        base_verdict = "correct" if tests["passed"] == tests["total"] and not failed else "incorrect" if not failed else "error"
    base = {
        "verdict": base_verdict,
        "headline": {"error": "Your code has an error", "works": "Your code ran successfully", "correct": "All tests passed", "incorrect": "Some tests failed"}[base_verdict],
        "explanation": _last_error_line(run.get("stderr", "")) if failed else "The program ran and finished without errors.",
        "errors": [{"line": _line_number(run.get("stderr", "")), "message": _last_error_line(run.get("stderr", "")), "fix": "Read the message above; it points to the line that failed."}] if failed else [],
        "time_complexity": t, "space_complexity": s, "complexity_explanation": note, "suggestions": [], "improved_code": "", "source": "offline",
    }
    if not gemini.is_configured():
        return base
    prompt = f"""Language: {language}
{('PROBLEM:\n' + problem[:2500]) if problem else 'No problem statement: the user is freely running their own code.'}

CODE:
```{language}
{code[:9000]}
```
RUN RESULT: exit_code={run.get('exit_code')}, timed_out={run.get('timed_out')}, phase={run.get('phase')}
STDOUT:
{run.get('stdout', '')[:2000]}
STDERR:
{run.get('stderr', '')[:2000]}
{('TESTS: ' + str(tests['passed']) + ' of ' + str(tests['total']) + ' passed. Failed visible cases: ' + str(tests.get('failed_visible', []))[:1500]) if tests else ''}

Return JSON: {{"verdict": "correct|incorrect|error|works",
 (error = it crashed/failed to compile/timed out; correct = produces the right result for the problem/tests; incorrect = runs but wrong; works = no problem given and it ran cleanly),
 "headline": "one short sentence",
 "explanation": "2-4 sentences explaining the result in plain language. If there is an error, say exactly what caused it.",
 "errors": [{{"line": number or null, "message": "", "fix": "how to fix it"}}],
 "time_complexity": "e.g. O(n log n)", "space_complexity": "e.g. O(n)",
 "complexity_explanation": "why, in 1-2 sentences",
 "suggestions": ["up to 3 improvements: edge cases, readability, a faster approach"],
 "improved_code": "a corrected or better version of the full code, or empty string if the code is already good"}}"""
    try:
        r = gemini.generate_json(prompt, system=SYSTEM, temperature=0.2, max_tokens=8192)
        verdict = str(r.get("verdict", base_verdict)).lower()
        if verdict not in ("correct", "incorrect", "error", "works"):
            verdict = base_verdict
        if failed:
            verdict = "error"                     # real execution results always win over the model's opinion
        elif tests:
            verdict = "correct" if tests["passed"] == tests["total"] else "incorrect"
        return {
            "verdict": verdict, "headline": str(r.get("headline", base["headline"]))[:200], "explanation": str(r.get("explanation", base["explanation"]))[:1500],
            "errors": [{"line": e.get("line") if isinstance(e.get("line"), int) else None, "message": str(e.get("message", ""))[:300], "fix": str(e.get("fix", ""))[:500]}
                       for e in (r.get("errors") or []) if isinstance(e, dict)][:6],
            "time_complexity": str(r.get("time_complexity", t))[:60], "space_complexity": str(r.get("space_complexity", s))[:60],
            "complexity_explanation": str(r.get("complexity_explanation", ""))[:500], "suggestions": str_list(r.get("suggestions"), 4),
            "improved_code": str(r.get("improved_code", ""))[:9000], "source": "gemini",
        }
    except (gemini.GeminiError, AttributeError, TypeError) as exc:
        log.warning("Gemini code analysis failed: %s", exc)
        return base
