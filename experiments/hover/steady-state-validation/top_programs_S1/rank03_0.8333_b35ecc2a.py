def entrypoint():
    return {
        "system_prompt": "You are a fact-checker. Be precise: when instructed to output a query, provide ONLY the query string. When instructed to output 'NO_ADDITIONAL_QUERY', provide ONLY that string. Never add extra text.",
        "steps": [
            {
                "number": 1,
                "title": "First-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Generate second-hop query 1",
                "step_type": "llm",
                "aim": "Identify one missing information path from first-hop evidence",
                "stage_action": (
                    "Read retrieved passages and determine one specific piece of evidence needed to verify the claim. "
                    "Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What key fact is missing from the retrieved passages? "
                    "What is the most precise query to find that fact?"
                ),
                "example_reasoning": (
                    "Claim: The capital of France is Paris.\n"
                    "Passages: [1] France | France is a country in Europe. [2] Paris | Paris is a city.\n"
                    "Missing fact: Is Paris the capital of France?\n"
                    "Query: Paris capital of France"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query 2",
                "step_type": "llm",
                "aim": "Identify a different missing information path from first-hop evidence",
                "stage_action": (
                    "Read retrieved passages and determine another specific piece of evidence (distinct from query 1) "
                    "needed to verify the claim. Write a concise search query that addresses a different aspect of the claim. "
                    "Synonyms are acceptable if they capture a different nuance. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What other key fact is missing? "
                    "How can we phrase a query that addresses a different aspect?"
                ),
                "example_reasoning": (
                    "Claim: The capital of France is Paris.\n"
                    "Passages: [1] France | France is a country in Europe. [2] Paris | Paris is a city.\n"
                    "Missing fact: What is the capital city of France?\n"
                    "Query: capital city of France"
                ),
                "dependencies": [1, 2],
            },
            {
                "number": 4,
                "title": "Second-hop retrieval (query 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 5,
                "title": "Second-hop retrieval (query 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Summarize evidence for third hop",
                "step_type": "llm",
                "aim": "Condense all evidence into key facts and identify remaining gaps",
                "stage_action": (
                    "Review all passages from first and second hops. Extract top 3 relevant facts "
                    "for verifying the claim and list up to three missing facts in order of importance."
                ),
                "reasoning_questions": (
                    "What are the most critical facts found? "
                    "What specific information is still needed to confirm/refute the claim?"
                ),
                "example_reasoning": (
                    "Claim: The capital of France is Paris.\n"
                    "Passages: [first-hop] France geography ... [second-hop] Paris landmarks ...\n"
                    "Summary: Found: France is a country, Paris is its largest city. Missing: Official designation of Paris as capital."
                ),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Formulate query for most critical missing evidence",
                "stage_action": (
                    "Based on the summary, write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the single most important missing fact? "
                    "How can we phrase the most effective query for it?"
                ),
                "example_reasoning": (
                    "Summary: ... Missing: Official designation of Paris as capital.\n"
                    "Query: Paris official capital of France"
                ),
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Third-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},
                },
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Gap analysis and fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient or generate final query",
                "stage_action": (
                    "Analyze all evidence. If the claim cannot be verified due to a missing critical fact (without which the claim cannot be confirmed or refuted), "
                    "output a search query for that fact. Otherwise, output 'NO_ADDITIONAL_QUERY'.\n"
                    "Provide ONLY the query or 'NO_ADDITIONAL_QUERY', no additional text."
                ),
                "reasoning_questions": (
                    "Has the claim been fully verified? "
                    "If not, what specific information is missing and can it be queried?"
                ),
                "example_reasoning": (
                    "Claim: The Eiffel Tower was built in 1889.\n"
                    "Evidence: ... Found: Eiffel Tower location and height, but no construction date.\n"
                    "Output: Eiffel Tower construction year"
                ),
                "dependencies": [6, 8],
            },
            {
                "number": 10,
                "title": "Fourth-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }
