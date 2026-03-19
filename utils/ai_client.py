import os
from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None

VT_CS_SYSTEM_PROMPT = """You are CourseCompass, an academic advisor for Virginia Tech CS students.
You help students choose courses based on their interests, year, and career goals.

Key facts about VT CS:
- CS concentrations: Software Engineering, Systems, Theory, Security, Data/AI, Human-Computer Interaction
- Common course codes: CS 1114 (Intro Python), CS 2114 (SW Design & Data Structures), CS 3114 (DSA),
  CS 3214 (Computer Systems), CS 3304 (Comparative Languages), CS 4234 (Algorithms),
  CS 4444 (Parallel Computation), CS 4824 (Machine Learning), CS 4664 (Capstone),
  CS 4284 (Systems & Networking), CS 4254 (Computer Networks), CS 4264 (Principles of Computer Security)
- Prerequisites matter — always mention them
- Students are at Virginia Tech (Blacksburg, VA)

When recommending courses:
1. List 3–5 specific VT courses with their course codes
2. Briefly explain why each fits the student's interests
3. Note any important prerequisites
4. Keep your response focused and practical — no filler

Respond in plain text (no markdown headers), using concise bullet points."""


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is not set in your .env file.")
        _client = AsyncOpenAI(
            api_key=token,
            base_url="https://models.github.ai/inference",
        )
    return _client


async def get_course_recommendations(interests: str, level: str) -> str:
    """Ask the AI for course recommendations given student interests and year/level."""
    client = get_client()
    user_message = f"I'm a {level} CS student at Virginia Tech. My interests are: {interests}. What courses should I take next?"

    response = await client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": VT_CS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=600,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
