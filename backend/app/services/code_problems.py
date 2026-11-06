"""Coding problems. Expected outputs always come from running a reference solution, never from the model's guess."""
import logging
import random

from app.services import code_runner, gemini
from app.services.gemini import clamp_int, str_list

log = logging.getLogger("interviewmate.problems")

FALLBACK = [
    dict(title="Two Sum", topic="Hashing", difficulty=1,
         statement="Given an array of integers and a target, print the 0-based indices i < j of the first pair whose values add up to the target (scan i from left, then j). A pair always exists.",
         input_format="Line 1: n. Line 2: n integers. Line 3: target.", output_format="Two indices separated by a space.", constraints="2 <= n <= 10^5",
         examples=[{"input": "4\n2 7 11 15\n9", "output": "0 1", "explanation": "2 + 7 = 9"}],
         inputs=["4\n2 7 11 15\n9", "3\n3 2 4\n6", "2\n3 3\n6", "5\n1 5 9 14 20\n23", "6\n-1 -2 -3 -4 -5 8\n3"],
         reference="n=int(input());a=list(map(int,input().split()));t=int(input())\nseen={}\nfor i,x in enumerate(a):\n    if t-x in seen:\n        print(seen[t-x],i);break\n    seen[x]=i"),
    dict(title="Valid Palindrome", topic="Strings", difficulty=1,
         statement="Given a string, print YES if it reads the same forwards and backwards after removing every non-alphanumeric character and ignoring case, otherwise print NO.",
         input_format="One line containing the string.", output_format="YES or NO.", constraints="1 <= length <= 10^5",
         examples=[{"input": "A man, a plan, a canal: Panama", "output": "YES", "explanation": "Cleaned string is amanaplanacanalpanama"}],
         inputs=["A man, a plan, a canal: Panama", "race a car", "No lemon, no melon", "ab", "12321"],
         reference="s=[c.lower() for c in input() if c.isalnum()]\nprint('YES' if s==s[::-1] else 'NO')"),
    dict(title="Maximum Subarray Sum", topic="Dynamic programming", difficulty=2,
         statement="Given an array of integers, print the largest possible sum of a non-empty contiguous subarray.",
         input_format="Line 1: n. Line 2: n integers.", output_format="One integer.", constraints="1 <= n <= 10^5, -10^4 <= a[i] <= 10^4",
         examples=[{"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "output": "6", "explanation": "Subarray [4, -1, 2, 1]"}],
         inputs=["9\n-2 1 -3 4 -1 2 1 -5 4", "1\n5", "5\n-3 -1 -2 -5 -4", "6\n5 4 -1 7 8 -20", "4\n1 2 3 4"],
         reference="n=int(input());a=list(map(int,input().split()))\nbest=cur=a[0]\nfor x in a[1:]:\n    cur=max(x,cur+x);best=max(best,cur)\nprint(best)"),
    dict(title="Count Word Frequency", topic="Hashing", difficulty=2,
         statement="Read a line of lowercase words separated by spaces. Print each distinct word with its count, sorted by count (highest first), then alphabetically for ties, one 'word count' pair per line.",
         input_format="One line of words.", output_format="Lines of 'word count'.", constraints="1 <= words <= 10^5",
         examples=[{"input": "to be or not to be", "output": "be 2\nto 2\nnot 1\nor 1", "explanation": "be and to appear twice"}],
         inputs=["to be or not to be", "a a a b b c", "hello", "x y z", "the cat and the hat and the bat"],
         reference="from collections import Counter\nc=Counter(input().split())\nfor w,k in sorted(c.items(),key=lambda t:(-t[1],t[0])):\n    print(w,k)"),
]


def _build(spec: dict) -> dict | None:
    """Run the reference solution on each input to get the true expected outputs."""
    tests = []
    for inp in spec["inputs"][:8]:
        r = code_runner.run_code("python", spec["reference"], inp + "\n")
        if r.unavailable or r.exit_code != 0 or r.timed_out:
            log.warning("Reference solution failed for %s: %s", spec["title"], r.stderr[:200])
            return None
        tests.append({"input": inp, "expected": r.stdout.strip()})
    return {"tests": tests} if len(tests) >= 3 else None


def generate(topic: str, level: int, avoid: list[str]) -> dict:
    spec = None
    if gemini.is_configured():
        prompt = f"""Create ONE original coding-interview problem solvable with standard input/output.
Topic: {topic or 'any'}. Difficulty: {level}/5. Random seed: {random.randint(1, 99999)}.
Do NOT reuse these earlier titles/statements: {avoid[:15]}
Rules: the program reads from stdin and prints to stdout, with a single unambiguous correct output for every input (no 'any valid answer' problems).
Return JSON: {{"title": "", "topic": "", "difficulty": 1-5, "statement": "", "input_format": "", "output_format": "", "constraints": "",
"examples": [{{"input": "", "output": "", "explanation": ""}}],
"inputs": [6 to 8 test inputs as exact stdin strings, including edge cases and one larger case],
"reference": "a CORRECT, complete Python 3 program that reads stdin and prints the expected output"}}"""
        try:
            r = gemini.generate_json(prompt, temperature=0.9, max_tokens=8192)
            if isinstance(r, dict) and r.get("reference") and isinstance(r.get("inputs"), list) and r.get("statement"):
                spec = {"title": str(r.get("title", "Problem"))[:100], "topic": str(r.get("topic", topic))[:80], "difficulty": clamp_int(r.get("difficulty"), 1, 5, level),
                        "statement": str(r["statement"])[:3000], "input_format": str(r.get("input_format", ""))[:500], "output_format": str(r.get("output_format", ""))[:500],
                        "constraints": str(r.get("constraints", ""))[:500],
                        "examples": [{"input": str(e.get("input", "")), "output": str(e.get("output", "")), "explanation": str(e.get("explanation", ""))}
                                     for e in (r.get("examples") or []) if isinstance(e, dict)][:3],
                        "inputs": [str(i) for i in r["inputs"] if isinstance(i, (str, int))][:8], "reference": str(r["reference"])}
        except (gemini.GeminiError, AttributeError, TypeError) as exc:
            log.warning("Gemini problem generation failed: %s", exc)
    built = _build(spec) if spec else None
    source = "gemini"
    if not built:
        joined = " ".join(avoid)
        pool = [p for p in FALLBACK if p["statement"][:100] not in joined] or FALLBACK
        spec = dict(random.choice(pool))
        built = _build(spec)
        source = "offline"
    if not built:
        raise RuntimeError("Could not prepare a coding problem")
    n_visible = min(2, len(built["tests"]))
    # Examples shown to the user are verified against the reference too.
    visible = [{"input": t["input"], "output": t["expected"], "explanation": ""} for t in built["tests"][:n_visible]]
    for ex, v in zip(spec.get("examples", []), visible):
        v["explanation"] = ex.get("explanation", "")
    return {"title": spec["title"], "topic": spec["topic"], "difficulty": spec["difficulty"], "statement": spec["statement"],
            "question": spec["statement"], "input_format": spec["input_format"], "output_format": spec["output_format"],
            "constraints": spec["constraints"], "examples": visible, "tests": built["tests"], "n_visible": n_visible,
            "reference_solution": spec["reference"], "source": source, "type": "code", "module": "coding", "kind": "coding"}


STARTERS = {
    "python": "# Read from standard input, print to standard output\n\ndef main():\n    pass\n\nif __name__ == \"__main__\":\n    main()\n",
    "javascript": "// Read all of stdin, print to stdout\nconst lines = require('fs').readFileSync(0, 'utf8').split('\\n');\n\n",
    "java": "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        \n    }\n}\n",
    "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    \n    return 0;\n}\n",
    "c": "#include <stdio.h>\n\nint main(void) {\n    \n    return 0;\n}\n",
}
