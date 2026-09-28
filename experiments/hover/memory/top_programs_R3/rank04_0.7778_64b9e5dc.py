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
            # Step 2: Analyze first-hop evidence and generate second-hop query (primary entities focus)
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify key entities from claim and verify basic facts using first-hop evidence.",
                "stage_action": (
                    "Read the claim and first-hop passages to verify basic entity facts. "
                    "If any entity details are missing or unverified, generate a precise search query for those specifics. "
                    "Output ONLY the search query string with no additional text; extra text causes retrieval failure."
                ),
                "reasoning_questions": (
                    "1. What are the primary entities in the claim that require verification?\n"
                    "2. Which entity details remain unverified by the first-hop evidence?\n"
                    "3. How can we precisely query missing entity attributes?"
                ),
                "example_reasoning": (
                    "Claim: 'Mount Everest's height is 8,848 meters above sea level.'\n"
                    "Retrieved passages:\n"
                    "  [1] Mount Everest | Elevation recorded as 8,848 m in 1955 Indian survey.\n"
                    "  [2] Himalayan Geography | Modern GPS measurements show 8,848 m ± 0.5 m.\n"
                    "Mount Everest current official height measurement"
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
            # Step 4: Analyze evidence and generate third-hop query (contradiction resolution focus)
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify contradictions between evidence and resolve with authoritative sources.",
                "stage_action": (
                    "Compare all retrieved evidence to find contradictions or ambiguities. "
                    "Generate a query targeting authoritative resolution of the conflict. "
                    "Output ONLY the search query string with no additional text; extra text causes retrieval failure."
                ),
                "reasoning_questions": (
                    "1. What specific contradiction exists between evidence passages?\n"
                    "2. Which authoritative source would resolve this conflict?\n"
                    "3. How to phrase the query for maximum resolution clarity?"
                ),
                "example_reasoning": (
                    "Claim: 'Vitamin C prevents common colds.'\n"
                    "Retrieved passages:\n"
                    "  [1] Medical Journal | Vitamin C shows no significant cold prevention in adults.\n"
                    "  [2] Nutrition Review | Regular vitamin C reduces cold duration but not incidence.\n"
                    "Cochrane review vitamin C cold prevention meta-analysis"
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
            # Step 6: Analyze evidence and generate fourth-hop query (authoritative resolution focus)
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify remaining verification gaps requiring definitive authoritative sources.",
                "stage_action": (
                    "Review all evidence to find unverified claims needing definitive sources. "
                    "Generate a query targeting primary sources or academic consensus. "
                    "Output ONLY the search query string with no additional text; extra text causes retrieval failure."
                ),
                "reasoning_questions": (
                    "1. What claim elements lack authoritative verification?\n"
                    "2. Which primary sources would provide definitive evidence?\n"
                    "3. How to phrase the query for academic source retrieval?"
                ),
                "example_reasoning": (
                    "Claim: 'Shakespeare wrote King Lear in 1605.'\n"
                    "Retrieved passages:\n"
                    "  [1] Shakespearean Timeline | King Lear composition dated between 1605-1606.\n"
                    "  [2] Folger Library | Earliest recorded performance was 1606.\n"
                    "Shakespeare First Folio King Lear publication year"
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