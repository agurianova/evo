def entrypoint():
    return {
        "system_prompt": "You are an evidence retrieval assistant. Your goal is to find all relevant Wikipedia passages to verify the claim. Always prioritize completeness of evidence. If after analysis there are still gaps, generate a query to fill the gap.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve first-hop passages (precision)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Summarize evidence and generate second-hop query",
                "step_type": "llm",
                "aim": "Extract key facts and identify missing information to verify the claim.",
                "stage_action": (
                    "Analyze the retrieved passages to verify the claim. Identify what evidence is present and what is missing. "
                    "Generate a search query for the next hop that covers multiple keyword variations to maximize recall. "
                    "Output ONLY the search query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The event occurred in 1887'. Retrieved passages mention 'completion in 1889' but not the start year. "
                    "Missing: start year. Query: 'event start year construction begin'"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Summarize evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Extract key facts and identify missing information to verify the claim.",
                "stage_action": (
                    "Analyze the retrieved passages to verify the claim. Identify what evidence is present and what is missing. "
                    "Generate a search query for the next hop that covers multiple keyword variations to maximize recall. "
                    "Output ONLY the search query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The material has high conductivity'. Retrieved passages discuss electrical properties but not thermal. "
                    "Missing: thermal conductivity. Query: 'material thermal conductivity heat transfer'"
                ),
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Summarize evidence and generate fourth-hop query",
                "step_type": "llm",
                "aim": "Extract key facts and identify missing information to verify the claim.",
                "stage_action": (
                    "Analyze the retrieved passages to verify the claim. Identify what evidence is present and what is missing. "
                    "Generate a search query for the next hop that covers multiple keyword variations to maximize recall. "
                    "Output ONLY the search query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The process requires 3 steps'. Retrieved passages describe 2 steps. "
                    "Missing: third step. Query: 'process final step completion phase'"
                ),
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Summarize evidence and generate fifth-hop query",
                "step_type": "llm",
                "aim": "Extract key facts and identify missing information to verify the claim.",
                "stage_action": (
                    "Analyze the retrieved passages to verify the claim. Identify what evidence is present and what is missing. "
                    "Generate a search query for the next hop that covers multiple keyword variations to maximize recall. "
                    "Output ONLY the search query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The component is made of titanium'. Retrieved passages confirm material but not grade. "
                    "Missing: titanium grade. Query: 'component titanium grade specification alloy'"
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Retrieve fifth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Final evidence synthesis and gap analysis",
                "step_type": "llm",
                "aim": "Synthesize evidence from all hops and identify any remaining verification gaps.",
                "stage_action": (
                    "Review all evidence from all hops. Do not stop until every aspect of the claim is verified. "
                    "Summarize the evidence found and list any remaining gaps in verification. "
                    "Provide a comprehensive analysis of how the evidence supports or refutes the claim."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The event occurred in 1887'. Evidence: Hop1: 'completion in 1889'; "
                    "Hop2: 'construction started in 1887'; Hop3: 'the term built refers to completion'. "
                    "Conclusion: The claim is false because 'built' refers to completion (1889), not start (1887). Gaps: None."
                ),
                "dependencies": [1, 3, 5, 7, 9],
            },
        ],
    }