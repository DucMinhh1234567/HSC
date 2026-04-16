"""Question generation layer — prompt engineering + Gemini LLM."""

from hsc_edu.generation.question_generator import (
    GeneratedQuestion,
    generate_for_textbook,
    generate_questions,
)

__all__ = [
    "GeneratedQuestion",
    "generate_for_textbook",
    "generate_questions",
]
