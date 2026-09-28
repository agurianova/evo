def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Always follow instructions precisely. For query generation steps, output ONLY the search query string with no additional text, formatting, or explanations.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve initial passages (first hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Analyze first-hop evidence and generate second-hop query",
                "step_type": "llm",
                "aim": "Extract key facts from initial retrieved passages, identify missing evidence, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and internally summarize relevant facts. Identify specific missing information needed for verification. "
                    "Then, generate a single search query string that covers multiple angles of the missing evidence using OR combinations (e.g., 'term1 OR term2'). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. What specific information is still missing to verify the claim?\n"
                    "5. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "6. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Crew | The crew included Neil Armstrong and Buzz Aldrin.\n"
                    "Relevant passages: [1] and [2] provide mission details and crew members.\n"
                    "Key facts: Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.\n"
                    "Summary: 'Apollo 11, with crew Neil Armstrong and Buzz Aldrin, landed on the moon on July 20, 1969.'\n"
                    "Missing: Neil Armstrong's role as the first person to step on the moon.\n"
                    "Possible queries: 'Neil Armstrong first man moon', 'Neil Armstrong first step moon', 'first person moon landing'\n"
                    "Neil Armstrong first man moon OR Neil Armstrong first step moon OR first person moon landing"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Analyze second-hop evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Extract key facts from second-hop retrieved passages, identify missing evidence, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and internally summarize relevant facts. Identify specific missing information needed for verification. "
                    "Then, generate a single search query string that covers multiple angles of the missing evidence using OR combinations (e.g., 'term1 OR term2'). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence connect to the original claim and previous evidence?\n"
                    "3. What specific information is still missing to verify the claim?\n"
                    "4. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "5. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Previous summary: 'Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.'\n"
                    "Passages:\n"
                    "[1] Moon landing | Neil Armstrong was the first human to step onto the lunar surface.\n"
                    "New evidence: Neil Armstrong was the first to step on the moon.\n"
                    "Summary: 'Neil Armstrong was the first human to step onto the lunar surface during Apollo 11.'\n"
                    "Missing: Official NASA confirmation of Armstrong's first step.\n"
                    "Possible queries: 'NASA Armstrong first step verification', 'NASA moon landing confirmation', 'official moon landing records'\n"
                    "NASA Armstrong first step verification OR NASA moon landing confirmation OR official moon landing records"
                ),
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Analyze third-hop evidence and generate fourth-hop query",
                "step_type": "llm",
                "aim": "Extract key facts from third-hop retrieved passages, identify missing evidence, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and internally summarize relevant facts. Identify specific missing information needed for verification. "
                    "Then, generate a single search query string that covers multiple angles of the missing evidence using OR combinations (e.g., 'term1 OR term2'). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence connect to the original claim and previous evidence?\n"
                    "3. What specific information is still missing to verify the claim?\n"
                    "4. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "5. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Previous summary: 'Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin; Neil Armstrong was the first human to step onto the lunar surface.'\n"
                    "Passages:\n"
                    "[1] NASA records | NASA officially documented Neil Armstrong as the first person on the moon.\n"
                    "New evidence: NASA officially documented Armstrong's role.\n"
                    "Summary: 'NASA officially documented Neil Armstrong as the first person to step on the moon during Apollo 11.'\n"
                    "Missing: Timestamp of Armstrong's first step.\n"
                    "Possible queries: 'Armstrong moon step time', 'first step moon timestamp', 'Apollo 11 step time'\n"
                    "Armstrong moon step time OR first step moon timestamp OR Apollo 11 step time"
                ),
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Analyze fourth-hop evidence and generate fifth-hop query",
                "step_type": "llm",
                "aim": "Extract key facts from fourth-hop retrieved passages, identify missing evidence, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and internally summarize relevant facts. Identify specific missing information needed for verification. "
                    "Then, generate a single search query string that covers multiple angles of the missing evidence using OR combinations (e.g., 'term1 OR term2'). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence connect to the original claim and previous evidence?\n"
                    "3. What specific information is still missing to verify the claim?\n"
                    "4. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "5. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Previous summary: 'NASA officially documented Neil Armstrong as the first person to step on the moon during Apollo 11.'\n"
                    "Passages:\n"
                    "[1] Timeline | Armstrong stepped onto the lunar surface at 02:56 UTC on July 21, 1969.\n"
                    "New evidence: Timestamp of Armstrong's first step.\n"
                    "Summary: 'Neil Armstrong stepped onto the lunar surface at 02:56 UTC on July 21, 1969.'\n"
                    "Missing: None - all claim elements are now verified.\n"
                    "Possible queries: (no missing information, but if needed) 'moon landing verification complete'\n"
                    "moon landing verification complete"
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Retrieve fifth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Synthesize all evidence and verify coverage",
                "step_type": "llm",
                "aim": "Synthesize all retrieved evidence from all hops to confirm verification coverage and identify any remaining gaps.",
                "stage_action": (
                    "Review all retrieved passages from all previous hops and create a comprehensive summary of evidence supporting the claim. "
                    "List any specific information still missing under 'Missing:'. Do not generate a search query."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which passages from all hops contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. Is the claim fully verified by the retrieved evidence? If not, what specific information is still missing?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Hop1 passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Crew | The crew included Neil Armstrong and Buzz Aldrin.\n"
                    "Hop2 passages:\n"
                    "[1] Moon landing | Neil Armstrong was the first human to step onto the lunar surface.\n"
                    "Hop3 passages:\n"
                    "[1] NASA records | NASA officially documented Neil Armstrong as the first person on the moon.\n"
                    "Hop4 passages:\n"
                    "[1] Timeline | Armstrong stepped onto the lunar surface at 02:56 UTC on July 21, 1969.\n"
                    "Hop5 passages: (none relevant)\n"
                    "Relevant passages: Hop1 [1,2], Hop2 [1], Hop3 [1], Hop4 [1].\n"
                    "Key facts: Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin; Neil Armstrong was the first human to step onto the lunar surface; NASA officially documented this; the step occurred at 02:56 UTC on July 21, 1969.\n"
                    "Summary: 'Apollo 11, with crew Neil Armstrong and Buzz Aldrin, landed on the moon on July 20, 1969. Neil Armstrong was the first human to step onto the lunar surface at 02:56 UTC on July 21, 1969, as officially documented by NASA.'\n"
                    "Missing: None - all claim elements are verified."
                ),
                "dependencies": [1, 3, 5, 7, 9],
            },
        ],
    }
