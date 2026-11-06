"""Skill vocabulary used for offline resume parsing and the deterministic part of job matching."""
import re

SKILLS = {
    "Languages": ["python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "golang", "rust", "kotlin", "swift", "php", "ruby", "scala", "r", "matlab", "sql", "bash", "dart"],
    "Web": ["html", "css", "react", "next.js", "angular", "vue", "node.js", "express", "django", "flask", "fastapi", "spring boot", "spring", "tailwind", "bootstrap", "rest", "graphql", "redux", "jquery", ".net"],
    "Data & AI": ["machine learning", "deep learning", "nlp", "computer vision", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras", "opencv", "power bi", "tableau", "excel", "data analysis", "data science", "statistics", "llm", "generative ai", "langchain", "spark", "hadoop"],
    "Databases": ["mysql", "postgresql", "mongodb", "sqlite", "oracle", "redis", "firebase", "dynamodb", "elasticsearch", "sql server"],
    "Cloud & DevOps": ["aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "ci/cd", "terraform", "linux", "git", "github", "gitlab", "nginx", "ansible"],
    "CS fundamentals": ["data structures", "algorithms", "oop", "dbms", "operating systems", "computer networks", "system design", "design patterns", "microservices", "agile", "scrum", "testing", "junit", "pytest", "selenium", "api"],
}
ALL_SKILLS = sorted({s for group in SKILLS.values() for s in group}, key=len, reverse=True)
CATEGORY = {s: g for g, items in SKILLS.items() for s in items}


def _pattern(skill: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9+#.])" + re.escape(skill) + r"(?![A-Za-z0-9+#])", re.I)


def find_skills(text: str) -> list[str]:
    found = []
    for s in ALL_SKILLS:
        if _pattern(s).search(text):
            found.append(s)
    return found


def has_skill(text: str, skill: str) -> bool:
    return bool(_pattern(skill).search(text))
