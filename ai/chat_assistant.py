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

Write a useful, objective business explanation using this structure:

OBJECTIVE ANSWER:
State the direct answer in 2-3 sentences. Use exact values, dates, rankings, and percentages
that are visible in the returned data. Do not delay the answer or repeat the question.

WHAT THE DATA SAYS:
Explain the important details in 3-5 sentences. Compare the strongest and weakest results,
describe a trend or unusual result when one is visible, and explain why the finding matters
to the business. Only make claims supported by the returned data.

PROBLEMS OR RISKS:
Explain 1-3 concerns suggested by the data in 2-4 sentences. If the data does not show a
clear problem, say that directly and identify what should be watched instead. Never invent
a cause, missing information, or business problem.

RECOMMENDED ACTION:
Give 2-3 practical actions in 2-4 sentences. Prioritise the most useful next step and make
it measurable where possible. Keep recommendations realistic and connected to the findings.

Style rules:
- Use simple, natural English that a non-technical business user can understand
- Use short paragraphs with the section labels above; do not use markdown tables
- Always include actual numbers from the data and clearly distinguish facts from suggestions
- Be balanced and objective; do not exaggerate or claim certainty the data cannot support
- Never mention SQL, databases, tables, columns, queries, or technical implementation details
- Do not say "This chart shows" or "Based on the data" as an empty opening

Your analysis:"""

    try:
        response = client.chat.completions.create(
            model      = MODEL,
            messages   = [
                {
                    "role"   : "system",
                    "content": (
                        "You are an expert business analyst who gives objective, detailed, "
                        "plain-English answers to non-technical business users. Separate "
                        "verified findings from recommendations, reference actual numbers, "
                        "and never invent facts. Never mention SQL, databases, tables, "
                        "columns, queries, or implementation details in the explanation."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens = 650,
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
    return (
        f"The analysis found {row_count} result(s). "
        f"The first result was {json.dumps(first_row, default=str)[:200]}. "
        "Review the returned results for a complete business conclusion."
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