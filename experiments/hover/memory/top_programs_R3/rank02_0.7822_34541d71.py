def entrypoint():
    return {
        "system_prompt": (
            "You are a meticulous fact-checker verifying claims using multi-hop evidence retrieval. "
            "Your goal is to retrieve all relevant evidence to verify the claim by performing necessary retrieval hops. "
            "When generating a search query, output ONLY the query string with no additional text. "
            "When analyzing evidence, focus exclusively on identifying missing information required to verify the claim."
        ),
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
            # Step 2: Analyze first-hop evidence and generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify foundational missing information from first-hop evidence for primary entities.",
                "stage_action": (
                    "Read the retrieved passages and determine what foundational information about primary entities is missing "
                    "to verify the claim. Then, write a concise search query to find that missing information. "
                    "Output ONLY the search query string with no additional text. Any extra text will cause the retrieval to fail."
                ),
                "reasoning_questions": (
                    "1. What are the primary entities and key facts mentioned in the claim?\n"
                    "2. What basic information about these entities is missing from the first-hop evidence?\n"
                    "3. How can we formulate a query to find this foundational information?"
                ),
                "example_reasoning": (
                    "Claim: 'Mount Everest is the tallest mountain in the world.'\n"
                    "Retrieved passages:\n"
                    "  [1] Mount Everest | Located in the Himalayas, it is the highest mountain above sea level.\n"
                    "  [2] Tallest mountains | Mount Everest is 8,848 meters tall.\n"
                    "Mount Everest elevation measurement method"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Analyze first+second hop evidence and generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify contradictions and resolve ambiguities across first two evidence hops.",
                "stage_action": (
                    "Read all retrieved passages from previous hops and determine what specific contradictions or gaps remain "
                    "to verify the claim. Then, write a concise search query to resolve these. "
                    "Output ONLY the search query string with no additional text. Any extra text will cause the retrieval to fail."
                ),
                "reasoning_questions": (
                    "1. After reviewing all evidence so far (first and second hops), what specific contradictions or gaps exist?\n"
                    "2. What precise detail would resolve the ambiguity?\n"
                    "3. How to phrase a query that targets authoritative sources for this detail?"
                ),
                "example_reasoning": (
                    "Claim: 'Vitamin C prevents the common cold.'\n"
                    "Retrieved passages (from first and second hops):\n"
                    "  [1] Common cold | Vitamin C has been studied for cold prevention with mixed results.\n"
                    "  [2] Linus Pauling | Nobel laureate who advocated high doses of vitamin C for colds.\n"
                    "  [3] Cochrane Review | High-quality evidence shows vitamin C does not prevent colds in general population.\n"
                    "Vitamin C common cold prevention Cochrane meta-analysis"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Analyze all evidence and generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final verification gaps requiring authoritative resolution.",
                "stage_action": (
                    "Read all retrieved passages from previous hops and determine the final missing verification element. "
                    "Then, write a concise search query targeting authoritative resolution. "
                    "Output ONLY the search query string with no additional text. Any extra text will cause the retrieval to fail."
                ),
                "reasoning_questions": (
                    "1. Given all evidence from previous hops, what is the final unresolved question?\n"
                    "2. Which authoritative source (e.g., government agency, academic consensus) would provide a definitive answer?\n"
                    "3. How to construct a query that retrieves that specific authoritative document?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in 1919.'\n"
                    "Retrieved passages (from all prior hops):\n"
                    "  [1] Treaty of Versailles | Officially signed on June 28, 1919.\n"
                    "  [2] World War I aftermath | The treaty was ratified in 1920.\n"
                    "  [3] Historical documents | The signing ceremony took place in the Hall of Mirrors.\n"
                    "Treaty of Versailles signing date official record"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }