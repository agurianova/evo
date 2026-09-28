def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to retrieve evidence to verify a claim through multi-hop reasoning. ALWAYS output search queries EXACTLY as requested with NO additional text. When filtering passages, include borderline cases with contextual relevance to claim entities. Focus only on facts directly relevant to the claim.",
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
            # Step 2: Filter first-hop passages with borderline examples
            {
                "number": 2,
                "title": "Filter claim-relevant passages",
                "step_type": "llm",
                "aim": "Identify passages directly relevant to claim verification including borderline cases.",
                "stage_action": (
                    "Review retrieved passages and output ONLY those containing information pertinent to the claim. "
                    "Include passages that mention claim entities even if missing specific facts (e.g., 'Eiffel Tower construction' without year). "
                    "Remove completely irrelevant passages. Preserve original passage format [i] Title | text."
                ),
                "reasoning_questions": (
                    "Which passages explicitly mention claim entities or facts? "
                    "Which passages provide contextual relevance (e.g., related events/entities)? "
                    "Which passages are completely irrelevant and should be discarded?"
                ),
                "example_reasoning": (
                    "Example: Claim 'Marie Curie won two Nobel Prizes.' Retrieved passages: "
                    "[0] Radioactivity | Curie discovered radium. [1] Nobel Prize | Marie Curie won in Physics (1903) and Chemistry (1911). [2] Einstein | ... "
                    "Relevant passages: [0] (mentions Curie and related work), [1] (directly states prizes)."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate first second-hop query with structured gap analysis
            {
                "number": 3,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify critical missing evidence through structured verification state analysis.",
                "stage_action": (
                    "Based on filtered passages, list: 1) Verified claim elements, 2) Missing critical facts. "
                    "Generate ONE precise search query targeting the MOST crucial missing fact. "
                    "Output ONLY the search query with no additional text."
                ),
                "reasoning_questions": (
                    "What specific claim elements are already verified by the evidence? "
                    "What is the SINGLE most critical missing fact for full verification? "
                    "How can we phrase a query that isolates this missing element?"
                ),
                "example_reasoning": (
                    "Example: Claim 'Mount Everest first summit 1953'. Evidence: "
                    "[1] Everest | World's highest mountain. [2] Hillary | New Zealand explorer. "
                    "Verified: mountain identity, explorer nationality. Missing: summit year and partner. "
                    "Query: 'Edmund Hillary Tenzing Norgay Everest summit year'"
                ),
                "dependencies": [2],
            },
            # Step 4: First second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: Filter second-hop passages with contextual relevance
            {
                "number": 5,
                "title": "Filter second-hop passages",
                "step_type": "llm",
                "aim": "Identify passages directly relevant to remaining verification gaps.",
                "stage_action": (
                    "Review retrieved passages and output ONLY those addressing missing claim elements. "
                    "Include passages with contextual relevance to unverified facts (e.g., '1953 expedition' without summit confirmation). "
                    "Remove irrelevant passages. Preserve original format [i] Title | text."
                ),
                "reasoning_questions": (
                    "Which passages address the specific missing facts identified in query generation? "
                    "Which provide contextual relevance to unverified claim elements? "
                    "Which should be discarded as irrelevant?"
                ),
                "example_reasoning": (
                    "Example: Missing 'summit year'. Retrieved: "
                    "[0] 1953 | British expedition to Everest. [1] Hillary | Summit achieved May 29. [2] Oxygen | Equipment used. "
                    "Relevant: [0] (mentions year and expedition), [1] (confirms summit). Irrelevant: [2]."
                ),
                "dependencies": [4],
            },
            # Step 6: Generate second second-hop query with multi-hop context
            {
                "number": 6,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify complementary missing evidence using multi-hop context.",
                "stage_action": (
                    "Based on ALL filtered evidence (first and second hop), list: "
                    "1) Verified claim elements, 2) Remaining critical gaps. "
                    "Generate ONE precise search query targeting the NEXT most crucial missing fact. "
                    "Output ONLY the search query with no additional text."
                ),
                "reasoning_questions": (
                    "What claim elements are now verified after two hops? "
                    "What is the SINGLE most critical remaining gap for verification? "
                    "How can we phrase a query that incorporates multi-hop context for precision?"
                ),
                "example_reasoning": (
                    "Example: Claim 'Python created by Guido van Rossum'. Evidence: "
                    "Hop1: [1] ABC language | Precursor to Python. Hop2: [0] CWI | Dutch research institute. "
                    "Verified: language precursor, creator's affiliation. Missing: creator's full name. "
                    "Query: 'Guido van Rossum ABC language successor creator'"
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Second second-hop retrieval
            {
                "number": 7,
                "title": "Retrieve second second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }