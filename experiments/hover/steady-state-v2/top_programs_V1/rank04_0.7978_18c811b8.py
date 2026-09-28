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
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify one critical missing information path and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, list one missing information required to verify the claim. "
                    "Then, write a concise search query to find this missing evidence.\n"
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
                "title": "Retrieve first branch passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Summarize first branch evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the first branch retrieved passages.",
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
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different missing information path and generate an alternative second-hop query.",
                "stage_action": (
                    "Using the first-hop summary, identify a distinct missing information path not covered by the first query. "
                    "Write a concise search query for this alternative evidence.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "First-hop summary: Paris is the capital city of France.\n"
                    "Reasoning: The first query focused on current population. Now we need historical context to verify trend.\n"
                    "Missing: Historical population growth of Paris.\n"
                    "Query: Paris population growth rate"
                ),
                "dependencies": [2],
            },
            {
                "number": 7,
                "title": "Retrieve second branch passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Summarize second branch evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second branch retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "Retrieved passages:\n"
                    "[1] Paris history | Paris population grew from 2.0 million in 2000 to 2.1 million in 2020.\n"
                    "Relevant facts: Confirms sustained population above 2 million.\n"
                    "Summary: Paris population grew steadily, remaining above 2 million since 2000."
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps using all evidence and generate third-hop query.",
                "stage_action": (
                    "Combine evidence from first-hop and both second-hop branches to identify any missing verification gaps. "
                    "Write a concise search query for the missing evidence.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The population of Paris is over 2 million.\n"
                    "First-hop summary: Paris is the capital city of France.\n"
                    "First branch summary: Population was 2.1 million in 2021.\n"
                    "Second branch summary: Population grew steadily, remaining above 2 million since 2000.\n"
                    "Reasoning: Evidence confirms population exceeds 2 million in multiple years. No gaps remain for verification.\n"
                    "Query:"
                ),
                "dependencies": [2, 5, 8],
            },
            {
                "number": 10,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }