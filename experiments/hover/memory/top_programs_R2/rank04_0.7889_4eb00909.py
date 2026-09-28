def entrypoint():
    return {
        "system_prompt": "You are a fact-checking assistant. Your task is to generate precise search queries for retrieving evidence to verify claims. Focus on key entities and specific terminology to maximize retrieval coverage. For query generation steps, output ONLY the search query string with no additional text.",
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
            # Step 2: Generate first query for second hop (branch A) with gap analysis
            {
                "number": 2,
                "title": "Generate first query for second hop (branch A)",
                "step_type": "llm",
                "aim": "Identify the most critical missing piece of evidence by analyzing gaps between the claim and first-hop passages, then generate a precise search query for it",
                "stage_action": (
                    "Based on the claim and first-hop passages, list the gaps in evidence that prevent full verification. "
                    "Then, select the most critical gap and write a concise search query targeting it. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific evidence is missing from the first-hop passages to verify the claim? List all gaps. "
                    "Which gap is the most critical to address first? "
                    "How can the query be formulated to target this gap precisely?"
                ),
                "example_reasoning": (
                    "Claim: 'Barack Obama was born in Honolulu.' First-hop passages: ['Barack Obama was born in Hawaii.']\n"
                    "Gaps: The passages mention Hawaii but not the specific city (Honolulu). Also missing: official documentation.\n"
                    "Most critical gap: The specific birth city.\n"
                    "Query: 'Barack Obama birth city Honolulu'"),
                "dependencies": [1],
            },
            # Step 3: First branch of second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve first branch of second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second query for second hop (branch B) with gap analysis
            {
                "number": 4,
                "title": "Generate second query for second hop (branch B)",
                "step_type": "llm",
                "aim": "Identify a different missing piece of evidence (distinct from branch A) by analyzing remaining gaps, then generate a precise search query",
                "stage_action": (
                    "Identify a gap in the evidence that is distinct from the gap addressed by the first query (from step 2) "
                    "and still present after reviewing first-hop and first branch second-hop passages. "
                    "Write a concise search query targeting this distinct gap. Avoid overlap with the first query. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific evidence is still missing after reviewing first-hop and first branch second-hop passages? "
                    "How is this gap different from the gap addressed by the first query (step 2)? "
                    "How can the query target this distinct gap without overlap?"
                ),
                "example_reasoning": (
                    "Claim: 'Barack Obama was born in Honolulu.' First-hop: ['Barack Obama was born in Hawaii.']. "
                    "First branch of second-hop: ['He was born in Honolulu, the capital of Hawaii.']\n"
                    "Gaps: The passages confirm Honolulu as birth city, but missing: official documentation (e.g., birth certificate).\n"
                    "Distinct gap: Official documentation.\n"
                    "Query: 'Barack Obama birth certificate Hawaii Department of Health'"),
                "dependencies": [1, 3],
            },
            # Step 5: Second branch of second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve second branch of second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Evidence synthesis and third hop decision with gap listing
            {
                "number": 6,
                "title": "Synthesize evidence and generate third hop query",
                "step_type": "llm",
                "aim": "Synthesize all evidence by claim elements to identify remaining gaps, then generate query only if needed",
                "stage_action": (
                    "Break down the claim into key factual elements. For each element, determine if supported by evidence "
                    "from all retrieved passages (first hop and both second-hop branches). If all elements are supported, "
                    "output an empty string. Otherwise, write a query for the most critical unsupported element. "
                    "Provide ONLY the search query (or empty string), no additional text."
                ),
                "reasoning_questions": (
                    "What are the key factual elements of the claim? For each element, is there supporting evidence? "
                    "Which elements remain unsupported? Is the evidence sufficient for verification? "
                    "If not, which unsupported element is most critical for a query?"
                ),
                "example_reasoning": (
                    "Example 1 (evidence complete):\n"
                    "Claim: 'Barack Obama was born in Honolulu.'\n"
                    "Key elements: birth location = Honolulu.\n"
                    "Passages:\n"
                    "  [1] 'Barack Obama was born in Hawaii.' -> does not specify city.\n"
                    "  [3] 'He was born in Honolulu, the capital of Hawaii.' -> specifies city as Honolulu.\n"
                    "  [5] 'The birth certificate is on file with the Hawaii Department of Health.' -> supports birth location.\n"
                    "Analysis: Birth location confirmed by [3] with official verification in [5]. All elements covered.\n"
                    "Output: ''\n\n"
                    "Example 2 (evidence incomplete):\n"
                    "Claim: 'Barack Obama was born in Honolulu.'\n"
                    "Key elements: birth location = Honolulu.\n"
                    "Passages:\n"
                    "  [1] 'Barack Obama was born in Hawaii.' -> does not specify city.\n"
                    "  [3] 'He was born in Honolulu, the capital of Hawaii.' -> specifies city as Honolulu.\n"
                    "  [5] 'The birth certificate exists but lacks verification details.' -> does not confirm city.\n"
                    "Analysis: Birth location confirmed by [3] but birth certificate lacks city verification.\n"
                    "Critical gap: birth certificate content verification.\n"
                    "Output: Barack Obama birth certificate content Honolulu"),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }