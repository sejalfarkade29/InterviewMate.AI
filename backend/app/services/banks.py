"""Offline question banks. Used when Gemini is unavailable and to make sure real, frequently asked
questions come first. HR questions below are the ones that appear most often in campus and
entry-level HR rounds (self-introduction, strengths/weaknesses, why-this-company, conflict, relocation...)."""

APTITUDE_TOPICS = ["Percentages", "Ratio and proportion", "Time and work", "Speed, time and distance", "Profit and loss",
                   "Simple and compound interest", "Probability", "Permutations and combinations", "Number series",
                   "Coding-decoding", "Blood relations", "Seating arrangement", "Syllogisms", "Data interpretation",
                   "Averages and mixtures", "Reading comprehension", "Error spotting", "Para jumbles"]
TECH_TOPICS = ["Python", "Java", "JavaScript", "SQL", "DBMS", "Operating systems", "Computer networks", "OOP", "System design basics",
               "REST APIs", "Git and version control", "Cloud and DevOps basics", "Debugging scenarios", "Testing"]
DSA_TOPICS = ["Arrays", "Strings", "Linked lists", "Stacks and queues", "Trees", "Graphs", "Dynamic programming", "Recursion and backtracking",
              "Sorting and searching", "Hashing", "Heaps", "Greedy", "Two pointers", "Sliding window", "Binary search"]
DAILY_KINDS = ["aptitude", "technical", "dsa", "hr", "sql", "logic puzzle", "predict the output", "system design mini", "project / behavioural"]

HR_MOST_ASKED = [
    ("Tell me about yourself.", "Introduction"),
    ("Why should we hire you?", "Motivation"),
    ("What are your strengths and weaknesses?", "Self-awareness"),
    ("Why do you want to join our company?", "Motivation"),
    ("Where do you see yourself in five years?", "Goals"),
    ("Tell me about a time you faced a conflict in a team and how you handled it.", "Conflict"),
    ("Tell me about your biggest achievement so far.", "Achievement"),
    ("Describe a failure or mistake and what you learned from it.", "Failure"),
    ("Are you willing to relocate or work in shifts?", "Flexibility"),
    ("How do you handle pressure and tight deadlines?", "Pressure"),
    ("Why did you choose this career path or branch?", "Motivation"),
    ("What do you know about our company?", "Research"),
    ("Tell me about a time you showed leadership.", "Leadership"),
    ("Tell me about a time you had to learn something quickly.", "Learning"),
    ("How would you handle a teammate who is not contributing?", "Teamwork"),
    ("What is your expected salary and how did you arrive at that number?", "Negotiation"),
    ("What are you looking for in your first job?", "Goals"),
    ("Describe a situation where you disagreed with your manager or mentor.", "Conflict"),
    ("How do you prioritise when you have many tasks at once?", "Time management"),
    ("Tell me about a project you are proud of and your exact role in it.", "Achievement"),
    ("What motivates you to work?", "Motivation"),
    ("Do you prefer working alone or in a team? Give an example.", "Teamwork"),
    ("How do you handle criticism or feedback?", "Feedback"),
    ("What would you do if you were given a task you had no idea how to start?", "Problem solving"),
    ("Why did you have a gap or low marks in some semester? (explain honestly)", "Gaps"),
    ("What are your hobbies and how do they help you at work?", "Personality"),
    ("Tell me about a time you went above and beyond.", "Initiative"),
    ("If you could change one thing about your college experience, what would it be?", "Reflection"),
    ("How would your friends or classmates describe you?", "Self-awareness"),
    ("Do you have any questions for us?", "Closing"),
    ("What will you do if you receive another offer with a higher package?", "Commitment"),
    ("Tell me about a time you persuaded someone to see things your way.", "Communication"),
    ("What is the one thing you would like us to know that is not on your resume?", "Introduction"),
    ("How do you stay updated with new technology?", "Learning"),
    ("Describe an ethical dilemma you faced and what you did.", "Ethics"),
]

APTITUDE_FALLBACK = [
    dict(topic="Percentages", difficulty=1, question="A service costs 80 after a 20% discount. What was the original price?", options=["90", "96", "100", "120"], answer_index=2, explanation="80 is 80% of the original, so 80 / 0.8 = 100."),
    dict(topic="Time and work", difficulty=2, question="A team completes 3 tasks in 6 hours. At the same rate, how long do 5 tasks take?", options=["8 hours", "9 hours", "10 hours", "12 hours"], answer_index=2, explanation="Each task takes 2 hours, so 5 tasks take 10 hours."),
    dict(topic="Number series", difficulty=1, question="Find the next number: 2, 6, 12, 20, 30, ?", options=["38", "40", "42", "44"], answer_index=2, explanation="Differences are 4, 6, 8, 10, so the next difference is 12 and 30 + 12 = 42."),
    dict(topic="Speed, time and distance", difficulty=2, question="A train 150 m long passes a pole in 10 seconds. What is its speed in km/h?", options=["45", "54", "60", "72"], answer_index=1, explanation="Speed = 150/10 = 15 m/s = 15 x 3.6 = 54 km/h."),
    dict(topic="Profit and loss", difficulty=2, question="An item bought for 500 is sold at a 12% profit. What is the selling price?", options=["540", "550", "560", "580"], answer_index=2, explanation="500 x 1.12 = 560."),
    dict(topic="Probability", difficulty=3, question="Two fair dice are rolled. What is the probability that the sum is 7?", options=["1/12", "1/9", "1/6", "5/36"], answer_index=2, explanation="Six of the 36 outcomes sum to 7, so 6/36 = 1/6."),
    dict(topic="Averages and mixtures", difficulty=3, question="The average of 5 numbers is 20. When one number is removed the average becomes 18. What number was removed?", options=["24", "26", "28", "30"], answer_index=2, explanation="Total was 100, new total is 72, so the removed number is 28."),
    dict(topic="Blood relations", difficulty=2, question="Pointing to a man, Asha says: 'His mother is the only daughter of my mother.' How is the man related to Asha?", options=["Brother", "Son", "Nephew", "Cousin"], answer_index=1, explanation="The only daughter of Asha's mother is Asha herself, so the man's mother is Asha and he is her son."),
]
TECH_FALLBACK = [
    dict(topic="OS", difficulty=1, question="Explain the difference between a process and a thread, and give one situation where it affects a design.", keywords=["process", "thread", "memory", "shared"], ideal_points=["Process has its own address space, threads share one", "Threads are cheaper to create and switch", "Shared memory needs synchronisation", "A crash in a process is isolated; in a thread it can take down the process"]),
    dict(topic="REST APIs", difficulty=2, question="Why would an API team choose pagination over returning every record at once? Mention one trade-off.", keywords=["pagination", "latency", "memory", "cursor", "offset"], ideal_points=["Bounds response size, memory and latency", "Offset vs cursor pagination", "Trade-off: consistency while data changes, or extra round trips"]),
    dict(topic="SQL", difficulty=2, question="What is the difference between INNER JOIN and LEFT JOIN? Describe a case where choosing the wrong one gives wrong results.", keywords=["inner", "left", "null", "unmatched"], ideal_points=["INNER keeps only matching rows", "LEFT keeps all left rows with NULLs for no match", "Reports that must include customers with no orders need LEFT JOIN"]),
    dict(topic="DBMS", difficulty=3, question="Describe how you would make a database-backed endpoint safe to retry after a network timeout.", keywords=["idempotent", "transaction", "key", "unique"], ideal_points=["Idempotency key stored with a unique constraint", "Wrap write in a transaction", "Return the stored result on retry"]),
    dict(topic="OOP", difficulty=1, question="What is polymorphism? Show a small example of runtime polymorphism in a language you know.", keywords=["override", "base", "derived", "interface"], ideal_points=["Same interface, different behaviour", "Method overriding resolved at runtime", "Example with a base class and two subclasses"]),
    dict(topic="Computer networks", difficulty=2, question="What happens, step by step, when you type a URL into a browser and press Enter?", keywords=["dns", "tcp", "http", "tls", "render"], ideal_points=["DNS lookup", "TCP handshake and TLS", "HTTP request and response", "Browser parses and renders"]),
]
DSA_FALLBACK = [
    dict(topic="Hashing", difficulty=1, question="Two Sum: given an array of integers and a target, return the indices of the two numbers that add up to the target. Explain your approach and its time and space complexity.", hints=["Brute force is O(n^2). Can you remember numbers you have already seen?", "A hash map from value to index lets you check the complement in O(1)."], keywords=["hash", "map", "complement", "o(n)"], ideal_points=["One pass with a hash map", "Time O(n), space O(n)"]),
    dict(topic="Sliding window", difficulty=2, question="Return the length of the longest substring without repeating characters. Explain the invariant of your window and the complexity.", hints=["Keep a window [l, r] with no duplicates.", "When s[r] is already in the window, move l past its previous index."], keywords=["window", "set", "map", "o(n)"], ideal_points=["Sliding window with last-seen index map", "Time O(n), space O(min(n, alphabet))"]),
    dict(topic="Linked lists", difficulty=2, question="Detect whether a singly linked list has a cycle and, if it does, find the node where the cycle begins. Explain complexity.", hints=["Two pointers moving at different speeds.", "After they meet, reset one to head and move both one step at a time."], keywords=["slow", "fast", "floyd", "o(1)"], ideal_points=["Floyd's tortoise and hare", "Time O(n), space O(1)"]),
    dict(topic="Binary search", difficulty=2, question="Given a rotated sorted array with distinct values, find the index of a target in O(log n). Explain the idea.", hints=["At least one half of [lo, mid] / [mid, hi] is always sorted.", "Check whether the target lies in the sorted half."], keywords=["binary", "sorted half", "o(log n)"], ideal_points=["Modified binary search", "Time O(log n), space O(1)"]),
    dict(topic="Dynamic programming", difficulty=3, question="Given coin denominations and a total, find the minimum number of coins needed to make the total (or -1). Explain the recurrence and complexity.", hints=["dp[x] = minimum coins for amount x.", "dp[x] = 1 + min(dp[x - c]) over coins c <= x."], keywords=["dp", "recurrence", "min", "o(n"], ideal_points=["Bottom-up DP over amounts", "Time O(amount x coins), space O(amount)"]),
]
HR_STAR_POINTS = ["Clear situation and your specific role", "Concrete actions you took (not 'we')", "Measurable or visible result", "What you learned and would do differently"]
