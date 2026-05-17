import os
import re
from typing import List
from groq import Groq

# ===============================
# 🔐 CONFIG
# ===============================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

MODEL = "llama-3.1-8b-instant"


# ===============================
# 🧠 SMART FALLBACK
# ===============================
def _smart_fallback(query: str, context_chunks: List[str]) -> str:
    if not context_chunks:
        return "I don't have specific experience on that topic yet, but I'm actively building in that area."

    best = re.sub(r'\s+', ' ', context_chunks[0].strip())
    sentences = [s.strip() for s in best.split('.') if len(s.strip()) > 20]
    opener = sentences[0] if sentences else best[:180]
    detail = sentences[1] if len(sentences) > 1 else ""

    return (
        f"So in that role, I worked on {opener.lower()}. "
        f"{detail + '.' if detail else ''} "
        "It went live and the team used it daily — it genuinely improved how we handled things end to end."
    ).strip()


# ===============================
# 🤖 MAIN LLM FUNCTION
# ===============================
def generate_answer(query: str, context_chunks: List[str]) -> str:

    top_chunks = _select_safe_chunks(context_chunks)
    context = "\n---\n".join(top_chunks)

    system_prompt = """You are helping a software engineering candidate answer interview questions naturally.

Convert the resume context into a spoken, first-person interview answer.

STRICT RULES:
- Output ONLY the answer — no preamble, no labels, no "Here's my answer:"
- First person only: "I", "my", "we"
- Exactly 4 to 5 sentences — no more, no less
- Zero bullet points, zero numbered lists, zero headings
- Spoken English tone — casual confidence, not formal resume language
- Use ALL specific details from the context: technology names, company names, metrics
- If context mentions LLaMA, WhatsApp, OCR, Gemini API — include them, they are impressive and must appear
- Never mix two different projects or companies in the same answer
- Never invent details not in the context

SENTENCE LENGTH RULE (critical):
- Every sentence must be speakable in one breath — maximum 25 words per sentence
- If a sentence exceeds 25 words, split it into two sentences at a natural conjunction
- Wrong: "I built a voice-to-text feature using LLaMA 3, which is a powerful model, and integrated it with WhatsApp so doctors could dictate notes on their phones."
- Right: "I built a voice-to-text feature using LLaMA 3. Doctors could dictate clinical notes directly through WhatsApp and have them filed automatically."

CLOSING RULE (critical):
- The final sentence MUST describe real-world deployment or usage
- Use patterns like:
  "The platform went live and is actively used by [users] to [do something specific]."
  "We shipped it to [X] users and it [specific measurable outcome]."
  "It's been running in production and [specific thing it does for real users]."
- NEVER end with vague phrases like: "improved efficiency", "made it accessible", "helped streamline processes", "improved overall experience"
- The closing must name WHO uses it and WHAT they actually do with it"""

    user_prompt = f"""Resume context (ONE project/role only — do not mix):
{context}

Interview question: {query}

Answer (4-5 short spoken sentences, all tech names included, ends with real deployment/usage):"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.65,
            max_tokens=300,
            top_p=0.9,
        )

        text = response.choices[0].message.content.strip()
        print(f"[GROQ] Raw: {text[:120]}...")

        if not text or len(text) < 50:
            return _smart_fallback(query, context_chunks)

        cleaned = _clean_output(text)

        if len(cleaned) < 80:
            return _smart_fallback(query, context_chunks)

        return cleaned

    except Exception as e:
        print(f"[GROQ ERROR] {e}")
        return _smart_fallback(query, context_chunks)


# ===============================
# ❓ FOLLOW-UP QUESTION GENERATOR
# ===============================
def generate_followups(query: str, answer: str, context_chunks: List[str]) -> List[str]:
    """
    Given the original question, the AI-generated answer, and resume context,
    generate 3 natural follow-up interview questions an interviewer would ask next.
    """

    top_chunks = _select_safe_chunks(context_chunks)
    context = "\n---\n".join(top_chunks)

    system_prompt = """You are an experienced technical interviewer.
Given a candidate's answer to an interview question, generate follow-up questions.

STRICT RULES:
- Output EXACTLY 3 follow-up questions, one per line
- Number them: 1. 2. 3.
- No preamble, no explanation, no blank lines between questions
- Each question must dig deeper into something specific the candidate mentioned
- Questions should feel natural — like a real interviewer probing further
- Mix question types: one technical deep-dive, one behavioural, one challenge/trade-off
- Keep each question under 20 words
- Never repeat the original question"""

    user_prompt = f"""Original question: {query}

Candidate's answer: {answer}

Resume context:
{context}

Generate 3 follow-up questions:"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=200,
            top_p=0.9,
        )

        text = response.choices[0].message.content.strip()
        print(f"[GROQ FOLLOWUP] Raw: {text[:120]}...")

        # Parse numbered lines → clean list
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        questions = []
        for line in lines:
            # Strip leading "1." / "2." / "3." etc.
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            if cleaned and len(cleaned) > 10:
                questions.append(cleaned)

        # Always return exactly 3 — pad with fallbacks if model short-circuits
        fallbacks = [
            "Can you walk me through a specific challenge you faced in that project?",
            "How would you scale that system if the user base grew 10x?",
            "What would you do differently if you built it again today?"
        ]
        while len(questions) < 3:
            questions.append(fallbacks[len(questions)])

        return questions[:3]

    except Exception as e:
        print(f"[GROQ FOLLOWUP ERROR] {e}")
        return [
            "Can you walk me through a specific challenge you faced in that project?",
            "How would you scale that system if the user base grew 10x?",
            "What would you do differently if you built it again today?"
        ]


# ===============================
# 🎯 SAFE CHUNK SELECTOR
# ===============================
def _select_safe_chunks(context_chunks: List[str]) -> List[str]:
    if len(context_chunks) <= 1:
        return context_chunks

    chunk1 = context_chunks[0].lower()
    chunk2 = context_chunks[1].lower()

    project_signals = [
        {"cloudmedi", "patient", "healthcare", "whatsapp", "llama", "clinical"},
        {"crispr", "sgrna", "dna", "biogru", "cas9", "gene"},
        {"blog", "mistral", "blip", "salesforce", "twitter", "reddit"},
    ]

    def detect_project(text: str) -> int:
        for i, signals in enumerate(project_signals):
            if any(kw in text for kw in signals):
                return i
        return -1

    p1 = detect_project(chunk1)
    p2 = detect_project(chunk2)

    if p1 != -1 and p2 != -1 and p1 != p2:
        print(f"[CHUNK GUARD] Dropping chunk 2 (project {p2} != project {p1})")
        return [context_chunks[0]]

    return context_chunks[:2]


# ===============================
# 🧹 OUTPUT CLEANER
# ===============================
def _clean_output(text: str) -> str:

    artifacts = [
        r'^(Answer|Response|Here\'s|Sure|Certainly|Of course|Great question)[:\s!]+',
        r'^\*+\s*',
        r'^#+\s*',
    ]
    for pattern in artifacts:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip()

    if text and text[-1] not in '.!?':
        text += '.'

    return text