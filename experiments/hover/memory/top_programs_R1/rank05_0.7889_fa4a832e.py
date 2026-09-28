def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. For multi-hop claims, break down the claim into distinct sub-questions. Generate diverse queries per hop to maximize evidence coverage. Focus on finding objective, factual evidence and avoid speculation. Always anchor your reasoning to the original claim. When generating queries, ensure they are 5-10 words long for simple claims, but allow up to 15 words for complex claims to capture necessary context. Always include at least two key entities. For parallel queries at the same hop, ensure they target distinct aspects and avoid overlapping terms.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate first second-hop query
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify one distinct missing piece of evidence and generate a high-quality search query for the second hop.",
                "stage_action": (
                    "Read the original claim and the first-hop retrieved passages. Extract key entities and dates. "
                    "Identify one specific gap in evidence needed to verify the claim. "
                    "Generate a concise search query that is 5-10 words long and contains at least two key entities. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key entities and dates are present? What is one specific missing piece of evidence? How can it be queried effectively?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "First-hop evidence: [1] Eiffel Tower | Built in Paris for 1889 World's Fair. [2] Barcelona | Major city in Spain.\n"
                    "Key entities/dates: Eiffel Tower, Barcelona, 1889\n"
                    "Missing evidence: Original intended location of Eiffel Tower\n"
                    "Query: 'Eiffel Tower original intended location Barcelona'"
                ),
                "dependencies": [1],
            },
            # Step 3: First second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve for first second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second second-hop query (now depends on first-hop and first second-hop results)
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different distinct missing piece of evidence (avoiding overlap with first query and its results) and generate high-quality search query for second hop.",
                "stage_action": (
                    "Read the original claim, first-hop passages, and first second-hop retrieved passages. Extract key entities and dates from all evidence. "
                    "Identify a different specific gap in evidence (distinct from first query's focus and not covered by first second-hop results) needed to verify the claim. "
                    "Generate a concise search query that is 5-10 words long, contains at least two key entities, and avoids terms from the first query and its results. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key entities/dates exist across claim and first-hop? What did first second-hop reveal? What is a different missing gap not covered? How to query without overlapping terms?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "First-hop evidence: [1] Eiffel Tower | Built in Paris for 1889 World's Fair. [2] Barcelona | Major city in Spain.\n"
                    "First second-hop retrieval (query 'Eiffel Tower original intended location Barcelona'): [1] Gustave Eiffel | Initially proposed Eiffel Tower for Barcelona exposition.\n"
                    "Key entities/dates: Eiffel Tower, Barcelona, 1889, Gustave Eiffel\n"
                    "First query: 'Eiffel Tower original intended location Barcelona'\n"
                    "Missing evidence: Official records of the Barcelona exposition proposal\n"
                    "Query: 'Barcelona 1888 exposition Eiffel Tower proposal'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Second second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve for second second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 6: Evidence sufficiency check and conditional third-hop query generation
            {
                "number": 6,
                "title": "Assess evidence sufficiency and generate third-hop query if needed",
                "step_type": "llm",
                "aim": "Determine if current evidence suffices for verification (>=80% coverage) or if third-hop retrieval is needed.",
                "stage_action": (
                    "Read the original claim and all retrieved passages so far (first-hop, first second-hop, second second-hop). "
                    "Extract key entities and dates from all evidence. Assess if evidence is sufficient to verify the claim (>=80% coverage). "
                    "If sufficient, output an empty string. "
                    "If insufficient, generate a concise search query (5-15 words) with at least two key entities for the most critical remaining gap. "
                    "Output exactly the query string (or empty string), no other content."
                ),
                "reasoning_questions": "What key entities/dates exist across all evidence? What is the most critical remaining gap? Is coverage >=80%?",
                "example_reasoning": (
                    "Insufficient case:\n"
                    "Claim: 'The Eiffel Tower was saved from demolition by the inventor of the radio.'\n"
                    "First-hop: [1] Eiffel Tower | Saved from demolition in 1909 for radio use.\n"
                    "First second-hop: [1] Gustave Ferrié | Used Eiffel Tower for military radio.\n"
                    "Second second-hop: [1] Radio transmission | Eiffel Tower enabled long-distance communication.\n"
                    "Key entities/dates: Eiffel Tower, demolition, 1909, radio, Gustave Ferrié\n"
                    "Remaining gap: Who invented radio and saved the tower?\n"
                    "Query: 'Marconi Eiffel Tower saved radio inventor'\n\n"
                    "Sufficient case:\n"
                    "Claim: 'The Eiffel Tower was built in Paris for the 1889 World's Fair.'\n"
                    "First-hop: [1] Eiffel Tower | Built in Paris for 1889 World's Fair.\n"
                    "First second-hop: [1] Paris | Capital of France.\n"
                    "Second second-hop: [1] World's Fair 1889 | Held in Paris.\n"
                    "Evidence covers all key facts.\n"
                    "Output: (empty string)"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third-hop retrieval (conditional)
            {
                "number": 7,
                "title": "Retrieve for third-hop query (if generated)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }