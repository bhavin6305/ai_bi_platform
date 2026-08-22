"""
chat_assistant.py
-----------------
Takes SQL query results and generates a plain-English business explanation
using Groq + Llama 3.1.

Called by: POST /api/chat (after sql_generator runs the query)
"""

import os
import json
import logging

from groq import Groq

logger = logging.getLogger(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL  = "openai/gpt-oss-120b"


def explain_results(
    question: str,
    sql_used: str,
    results : list[dict],
) -> str:
    if not results:
        return (
            "The query returned no results. This could mean the data doesn't "
            "contain matching records for your question. Try rephrasing with "
            "different filters or a broader time range."
        )

    sample     = results[:30]
    results_str = json.dumps(sample, indent=2, default=str)
    row_count  = len(results)

    prompt = f"""You are a senior business analyst at a top consulting firm.
A business executive has asked you a question about their data.
Your job is to explain the findings clearly, specifically, and helpfully.

EXECUTIVE'S QUESTION: "{question}"

DATA RETURNED ({row_count} rows total, showing up to 30):
{results_str}

Write your analysis following this structure:

1. DIRECT ANSWER (1 sentence): State the key finding immediately with specific numbers.
2. KEY DETAILS (2-3 sentences): Explain what the numbers mean in business terms.
   - Mention the top performer / worst performer if applicable
   - Include percentages, comparisons, or trends if visible in the data
   - Point out anything surprising or worth attention
3. RECOMMENDATION (1 sentence): Suggest one specific action the business could take.

Style rules:
- Use plain English — no SQL, no technical terms, no mention of tables or columns
- Be specific — always include actual numbers from the data
- Write in paragraph form, not bullet points
- Sound like a confident analyst, not a robot

Your analysis:"""

    try:
        response = client.chat.completions.create(
            model      = MODEL,
            messages   = [
                {
                    "role"   : "system",
                    "content": (
                        "You are an expert business analyst who explains data insights "
                        "to non-technical executives. You are direct, specific, and always "
                        "reference actual numbers from the data. You never mention SQL, "
                        "databases, tables, or columns in your responses."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens = 400,
            temperature= 0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Explanation generation failed: %s", e)
        return _fallback_summary(question, results)


def _fallback_summary(question: str, results: list[dict]) -> str:
    """Simple fallback summary when Groq API is unavailable."""
    if not results:
        return "No data found for your query."
    row_count = len(results)
    first_row = results[0]
    keys      = list(first_row.keys())
    return (
        f"Found {row_count} result(s). "
        f"Columns: {', '.join(keys[:5])}. "
        f"First result: {json.dumps(first_row, default=str)[:200]}."
    )
def suggest_followup_questions(
    question: str,
    answer  : str,
    results : list[dict],
) -> list[str]:
    """Generate 3 follow-up questions based on the chat context."""
    try:
        prompt = f"""Based on this Q&A about business data, suggest 3 short follow-up questions.

Previous question: "{question}"
Answer summary: "{answer[:200]}"

Generate exactly 3 follow-up questions, one per line, no numbering.
Questions should dig deeper into the data or explore related angles.
Keep each question under 10 words."""

        response = client.chat.completions.create(
            model      = MODEL,
            messages   = [{"role": "user", "content": prompt}],
            max_tokens = 80,
            temperature= 0.6,
        )
        lines = response.choices[0].message.content.strip().split("\n")
        return [q.strip() for q in lines if q.strip()][:3]
    except Exception:
        return []