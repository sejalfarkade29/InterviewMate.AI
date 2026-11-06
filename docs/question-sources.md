# Question sources and persistence

InterviewMate uses original practice prompts organized around the topic structure of reputable practice sites rather than copying their question text. HackerRank’s official Interview Preparation Kit is linked for optional topic-level practice: https://www.hackerrank.com/interview/interview-preparation-kit.

The frontend rotates local prompts by adaptive level, records question IDs and source links, and can synchronize completed attempts to the authenticated `/api/attempts` endpoint. The backend stores attempts in the project database in the `question_attempts` table, scoped by `user_id` and deduplicated by the browser-generated client ID.

Voice interview and HR flows use the browser Web Speech API when available. SpeechRecognition support varies by browser, so the UI always retains typed transcript entry as a fallback. The current implementation does not claim to provide a provider-specific live voice model when that provider is not configured.
