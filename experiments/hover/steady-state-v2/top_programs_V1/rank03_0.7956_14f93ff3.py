def entrypoint():
    return {
        "system_prompt": "You are an evidence specialist focused on verifying claims through multi-hop retrieval. Your goal is to maximize retrieval coverage by generating precise queries and concise evidence summaries. Always prioritize finding all relevant evidence, even if it requires multiple hops. In query generation steps, output ONLY the search query string with no additional text.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "Retrieved passages:\n"
                    "[1] Paris | Paris is the capital of France.\n"
                    "[2] France | France is a country in Western Europe.\n"
                    "Relevant facts: Paris is the capital of France (directly related to claim subject).\n"
                    "Summary: Paris is the capital city of France."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, list the missing information required to verify the claim. "
                    "Then, write a concise search query to find the missing evidence.\n"
                    "IMPORTANT: Your response must contain ONLY the search query and nothing else."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "First-hop summary: Paris is the capital city of France.\n"
                    "Reasoning: The claim requires population data, but the summary only confirms Paris' status as capital.\n"
                    "Missing: Current population figure of Paris.\n"
                    "Query: current population of Paris"
                ),
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "Retrieved passages:\n"
                    "[1] Demographics of Paris | As of 2021, the population of Paris was 2.1 million.\n"
                    "Relevant facts: Population figure matches claim requirement.\n"
                    "Summary: Paris had a population of 2.1 million in 2021."
                ),
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps using all evidence and generate third-hop query.",
                "stage_action": (
                    "Combine evidence from first and second hop summaries to identify missing information. "
                    "Write a concise search query for the missing evidence.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "First-hop summary: Paris is the capital city of France.\n"
                    "Second-hop summary: Paris had a population of 2.1 million in 2021.\n"
                    "Reasoning: The claim requires confirmation that population exceeds 2 million. Current evidence shows 2.1M in 2021, but we need to verify if this is the latest figure.\n"
                    "Missing: Most recent population estimate.\n"
                    "Query: latest population of Paris"
                ),
                "dependencies": [2, 5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "Retrieved passages:\n"
                    "[1] Paris population 2023 | The estimated population of Paris in 2023 is 2.16 million.\n"
                    "Relevant facts: Confirms population exceeds 2 million with recent data.\n"
                    "Summary: Paris population was estimated at 2.16 million in 2023."
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final gaps using all evidence and generate fourth-hop query.",
                "stage_action": (
                    "Combine evidence from all previous summaries to identify any remaining verification gaps. "
                    "Write a concise search query for the missing evidence.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "First-hop: Paris is capital of France.\n"
                    "Second-hop: Population was 2.1 million in 2021.\n"
                    "Third-hop: Population was 2.16 million in 2023.\n"
                    "Reasoning: Evidence confirms population exceeds 2 million in both 2021 and 2023. No gaps remain for verification.\n"
                    "Query: (none needed - but if gaps existed: source of population data)"
                ),
                "dependencies": [2, 5, 8],
            },
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }