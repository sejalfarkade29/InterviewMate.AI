"""Run user code with a timeout. Runs on THIS machine in a temp folder.

This is meant for local development and your own practice. It limits time and output, but it is not a
security sandbox. Before hosting InterviewMate publicly, replace `run_code` with Docker/Judge0 or similar.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass

from app.core.config import settings

MAX_OUTPUT = 20_000
LANGS = {"python": "Python", "javascript": "JavaScript", "java": "Java", "cpp": "C++", "c": "C"}


@dataclass
class RunResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    timed_out: bool = False
    duration_ms: int = 0
    phase: str = "run"          # "compile" if compilation failed
    unavailable: str = ""       # set when the language runtime is not installed

    def to_dict(self) -> dict:
        return asdict(self)


def available_languages() -> dict[str, bool]:
    return {
        "python": True,
        "javascript": bool(shutil.which("node")),
        "java": bool(shutil.which("javac") and shutil.which("java")),
        "cpp": bool(shutil.which("g++") or shutil.which("clang++")),
        "c": bool(shutil.which("gcc") or shutil.which("clang")),
    }


def _limits():
    if os.name != "posix":
        return None
    import resource

    def apply():
        resource.setrlimit(resource.RLIMIT_CPU, (settings.CODE_RUN_TIMEOUT_SECONDS + 2, settings.CODE_RUN_TIMEOUT_SECONDS + 2))
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
        os.setsid()
    return apply


def _env() -> dict:
    keep = {"PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "JAVA_HOME", "LANG"}
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _exec(cmd: list[str], cwd: str, stdin: str, timeout: int) -> tuple[subprocess.CompletedProcess | None, bool]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, env=_env(), preexec_fn=_limits())
        return proc, False
    except subprocess.TimeoutExpired:
        return None, True


def _clip(s: str) -> str:
    return s if len(s) <= MAX_OUTPUT else s[:MAX_OUTPUT] + "\n... output truncated ..."


def run_code(language: str, code: str, stdin: str = "") -> RunResult:
    if language not in LANGS:
        return RunResult(stderr="Unsupported language", exit_code=1)
    if not settings.CODE_RUN_ENABLED:
        return RunResult(unavailable="Code execution is disabled on this server (CODE_RUN_ENABLED=false).")
    if not available_languages()[language]:
        need = {"javascript": "Node.js", "java": "a JDK (javac + java)", "cpp": "g++ or clang++", "c": "gcc or clang"}[language]
        return RunResult(unavailable=f"{LANGS[language]} is not installed on the machine running the backend. Install {need}, or use Python.")
    timeout = settings.CODE_RUN_TIMEOUT_SECONDS
    with tempfile.TemporaryDirectory(prefix="im-run-") as tmp:
        start = time.perf_counter()
        if language == "python":
            path = os.path.join(tmp, "main.py")
            open(path, "w", encoding="utf-8").write(code)
            cmd, compile_cmd = [sys.executable, "-B", path], None
        elif language == "javascript":
            path = os.path.join(tmp, "main.js")
            open(path, "w", encoding="utf-8").write(code)
            cmd, compile_cmd = [shutil.which("node"), path], None
        elif language == "java":
            m = re.search(r"public\s+(?:final\s+)?class\s+(\w+)", code)
            cls = m.group(1) if m else "Main"
            path = os.path.join(tmp, f"{cls}.java")
            open(path, "w", encoding="utf-8").write(code)
            compile_cmd, cmd = [shutil.which("javac"), path], [shutil.which("java"), "-Xmx256m", "-cp", tmp, cls]
        else:
            ext = "cpp" if language == "cpp" else "c"
            path = os.path.join(tmp, f"main.{ext}")
            open(path, "w", encoding="utf-8").write(code)
            exe = os.path.join(tmp, "prog.exe" if os.name == "nt" else "prog")
            comp = (shutil.which("g++") or shutil.which("clang++")) if language == "cpp" else (shutil.which("gcc") or shutil.which("clang"))
            compile_cmd = [comp, path, "-O2", "-o", exe] + (["-std=c++17"] if language == "cpp" else [])
            cmd = [exe]
        if compile_cmd:
            proc, timed_out = _exec(compile_cmd, tmp, "", 30)
            if timed_out or proc is None or proc.returncode != 0:
                msg = "Compilation timed out" if timed_out or proc is None else _clip((proc.stderr or proc.stdout).replace(tmp, ""))
                return RunResult(stderr=msg, exit_code=1, phase="compile", duration_ms=int((time.perf_counter() - start) * 1000))
        t0 = time.perf_counter()
        proc, timed_out = _exec(cmd, tmp, stdin, timeout)
        ms = int((time.perf_counter() - t0) * 1000)
        if timed_out or proc is None:
            return RunResult(stderr=f"Time limit exceeded ({timeout}s). Check for an infinite loop or waiting on input.", timed_out=True, duration_ms=ms, exit_code=None)
        return RunResult(stdout=_clip(proc.stdout), stderr=_clip(proc.stderr.replace(tmp, "")), exit_code=proc.returncode, duration_ms=ms)


def normalize(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())
