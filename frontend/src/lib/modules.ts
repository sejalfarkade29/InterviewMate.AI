export type ModuleInfo = {
  slug: string;
  title: string;
  group: "Prepare" | "Interview rounds" | "Insights";
  phase: number;
  summary: string;
  includes: string[];
};

// Every module below is available in the interactive Preview workspace.
export const MODULES: ModuleInfo[] = [
  { slug: "resume", title: "Resume analyzer", group: "Prepare", phase: 5,
    summary: "Upload your resume (PDF, DOCX or TXT) to see exactly what it contains, how good it is, and which parts read as AI-written.",
    includes: ["File upload with validation", "Everything found in the resume, quality score in %", "AI-written areas highlighted"] },
  { slug: "job-match", title: "Job match", group: "Prepare", phase: 6,
    summary: "Paste a job description and it is matched against your analyzed resume to show what fits and what is missing.",
    includes: ["Required and preferred skill extraction", "Match score with an explanation of how it was calculated", "Saved job descriptions"] },
  { slug: "roadmap", title: "Preparation roadmap", group: "Prepare", phase: 15,
    summary: "A study plan built from your real results, with the reason behind each recommendation.",
    includes: ["Weak-topic identification", "Weekly targets and daily goals", "Progress tracking"] },
  { slug: "daily", title: "Daily challenges", group: "Prepare", phase: 16,
    summary: "A new challenge every time, of a different type, with one answer box, a score and feedback.",
    includes: ["Aptitude, technical, DSA, HR and project challenges", "Streak tracking", "Score and feedback after each answer"] },
  { slug: "simulation", title: "Full simulation", group: "Interview rounds", phase: 13,
    summary: "Run several rounds back to back, the way a real recruitment process works.",
    includes: ["Choose role, level, difficulty and rounds", "Round-by-round results", "Final readiness report"] },
  { slug: "aptitude", title: "Aptitude test", group: "Interview rounds", phase: 7,
    summary: "Timed multiple-choice tests on quantitative, logical and verbal topics.",
    includes: ["Configurable length, difficulty and negative marking", "Automatic scoring with explanations", "Topic-wise accuracy and time analysis"] },
  { slug: "technical", title: "Technical interview", group: "Interview rounds", phase: 8,
    summary: "An interviewer that asks one question at a time and follows up on your answers.",
    includes: ["Python, Java, SQL, DBMS, OS, networks and more", "Adaptive difficulty", "Structured feedback after the interview"] },
  { slug: "dsa", title: "DSA practice", group: "Interview rounds", phase: 9,
    summary: "Topic-wise data structures and algorithms problems, from beginner to advanced.",
    includes: ["Hints and solution explanations", "Complexity analysis", "Weak-topic tracking"] },
  { slug: "coding", title: "Live coding", group: "Interview rounds", phase: 9,
    summary: "A code editor with visible and hidden test cases, run in an isolated sandbox.",
    includes: ["Python, Java, C++ and JavaScript", "Real test execution, not AI guesses", "Submission history"] },
  { slug: "voice", title: "Voice interview", group: "Interview rounds", phase: 10,
    summary: "Speak with an AI interviewer in real time.",
    includes: ["Live microphone conversation", "Interviewer styles from friendly to strict", "Transcript, saved only with your consent"] },
  { slug: "hr", title: "HR interview", group: "Interview rounds", phase: 11,
    summary: "Behavioural questions scored against the STAR method.",
    includes: ["Common HR and situational questions", "Structure and clarity feedback", "Improved-answer suggestions based on your own experience"] },
  { slug: "project", title: "Project interview", group: "Interview rounds", phase: 11,
    summary: "Questions about your own projects, generated from your resume.",
    includes: ["Architecture, decisions and trade-offs", "Follow-ups based on your answers", "Help explaining projects clearly"] },
  { slug: "group-discussion", title: "Group discussion", group: "Interview rounds", phase: 12,
    summary: "Practice a timed discussion with an AI moderator and simulated participants.",
    includes: ["Topic selection", "Feedback on reasoning, clarity and listening", "Full transcript"] },
  { slug: "rewards", title: "Rewards & levels", group: "Insights", phase: 18,
    summary: "Earn XP for every answer, level up, keep a daily streak and collect badges.",
    includes: ["XP and level progress", "Daily streak", "Badges"] },
  { slug: "analytics", title: "Analytics", group: "Insights", phase: 14,
    summary: "Score trends and topic-wise accuracy drawn only from your saved results.",
    includes: ["Round-wise performance", "Strongest and weakest topics", "Improvement over time"] },
  { slug: "history", title: "Interview history", group: "Insights", phase: 17,
    summary: "Every past interview, with transcripts and reports you can export or delete.",
    includes: ["Searchable history", "PDF report export", "Data deletion controls"] },
];

export const GROUPS: ModuleInfo["group"][] = ["Prepare", "Interview rounds", "Insights"];

export const ROUNDS = [
  { name: "Aptitude test", note: "Quantitative, logical and verbal questions under a timer." },
  { name: "Technical interview", note: "Concepts, debugging and scenarios in your chosen subjects." },
  { name: "DSA interview", note: "Data structures and algorithms discussed out loud." },
  { name: "Live coding", note: "Solve problems in an editor and run them against test cases." },
  { name: "Group discussion", note: "Make your case and respond to other participants." },
  { name: "Project interview", note: "Defend the decisions in your own projects." },
  { name: "HR interview", note: "Behavioural questions answered with the STAR method." },
  { name: "Final evaluation", note: "A report built from the rounds you completed." },
];
