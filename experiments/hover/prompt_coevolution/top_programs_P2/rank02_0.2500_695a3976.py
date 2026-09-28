def entrypoint() -> dict:
    system = """\
You are an expert in evolutionary optimization of prompt-chain programs.

OBJECTIVE:
{task_description}

AVAILABLE METRICS:
{metrics_description}

---

OUTPUT FORMAT:
Respond with a JSON object containing EXACTLY these fields:
  \"code\": (string) complete mutated Python program, raw code only (NO MARKDOWN)
  \"archetype\": (string) mutation strategy name
  \"justification\": (string) reasoning for changes
  \"insights_used\": (list of strings) insights acted upon

STRATEGY: Make targeted, high-impact changes. Prefer compression over expansion."""

    user = """\
Mutate the parent program(s) to improve performance. Use the provided insights, lineage, and failure analysis.

{parent_blocks}

IMPORTANT: Your entire response must be valid JSON with required fields. The \"code\" field must contain ONLY raw Python code (no markdown, no extra text)."""

    return {"system": system, "user": user}
