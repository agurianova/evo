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
                "title": "Generate direct evidence query (second hop)",
                "step_type": "llm",
                "aim": "Extract key facts directly supporting or refuting the claim and generate a focused search query for missing direct evidence.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly relate to the claim. "
                    "Determine what specific direct evidence is still missing. "
                    "Generate a single search query string that uses OR combinations to cover multiple precise phrasings of the missing direct evidence. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which passages contain facts directly supporting/refuting the claim?\n"
                    "3. What specific direct evidence is still missing?\n"
                    "4. What are 2-3 precise search terms for this missing evidence?\n"
                    "5. How to combine them using OR for maximum recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Landed on moon July 20, 1969\n"
                    "[2] Crew | Included Neil Armstrong and Buzz Aldrin\n"
                    "Direct evidence found: Mission date and crew members.\n"
                    "Missing direct fact: Armstrong's role as first person to step on moon.\n"
                    "Neil Armstrong first step moon OR first person lunar surface OR Armstrong moonwalk timestamp"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate contextual evidence query (second hop)",
                "step_type": "llm",
                "aim": "Identify contextual information indirectly supporting the claim and generate a search query for missing background evidence.",
                "stage_action": (
                    "Read the retrieved passages and identify relevant context or background information. "
                    "Determine what specific contextual evidence is still missing to build a complete verification picture. "
                    "Generate a single search query string that uses OR combinations to cover multiple contextual angles of the missing evidence. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What historical context surrounds the claim?\n"
                    "2. What background information would indirectly support verification?\n"
                    "3. What specific contextual evidence is missing?\n"
                    "4. What are 2-3 contextual search terms for this gap?\n"
                    "5. How to combine them using OR for broad coverage?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Landed on moon July 20, 1969\n"
                    "[2] Crew | Included Neil Armstrong and Buzz Aldrin\n"
                    "Context found: Mission details and crew.\n"
                    "Missing context: NASA's official announcement of Armstrong's role.\n"
                    "NASA Armstrong first man statement OR White House moon landing announcement OR 1969 presidential address moon landing"
                ),
                "dependencies": [1],
            },
            {
                "number": 4,
                "title": "Retrieve direct passages (second hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 5,
                "title": "Retrieve contextual passages (second hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Merge evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Synthesize evidence from all previous hops, identify critical gaps, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Review all retrieved passages from hops 1, 2a, and 2b. Create a concise verification status summary. "
                    "Identify the single most critical missing piece of evidence. "
                    "Generate a single search query string that uses OR combinations to cover multiple precise phrasings of this gap. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What evidence has been verified so far across all passages?\n"
                    "2. What is the most critical missing verification element?\n"
                    "3. What are 2-3 highly specific search terms for this gap?\n"
                    "4. How to structure the query for maximum precision?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Previous evidence: Apollo 11 launched July 16, landed July 20, 1969.\n"
                    "Passages from hop2:\n"
                    "[1] NASA archives | 'First manned lunar landing completed in 1969'\n"
                    "[2] Press coverage | 'Historic 1969 moon mission'\n"
                    "Verified: Mission occurred in 1969.\n"
                    "Critical gap: Official timestamp of lunar module touchdown.\n"
                    "Apollo 11 lunar module touchdown time OR Eagle landing timestamp OR 1969 moon landing exact time"
                ),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Analyze third-hop evidence and generate fourth-hop query",
                "step_type": "llm",
                "aim": "Evaluate new evidence, update verification status, and generate a highly targeted query for remaining gaps.",
                "stage_action": (
                    "Read the newly retrieved passages and integrate with all previous evidence. "
                    "Determine if any critical verification gaps remain. "
                    "Generate a single search query string that uses OR combinations for the most precise remaining gap terms. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does it connect to previous evidence?\n"
                    "3. What is the final critical verification gap?\n"
                    "4. What are the most precise search terms for this gap?"
                ),
                "example_reasoning": (
                    "Claim: 'The Great Wall of China is visible from space.'\n"
                    "Previous evidence: Wall difficult to see with naked eye from orbit.\n"
                    "New passages:\n"
                    "[1] Astronaut reports | Requires binoculars for clear view\n"
                    "Verified: Not visible to naked eye.\n"
                    "Critical gap: Official NASA position documentation.\n"
                    "NASA Great Wall visibility statement OR official NASA position document OR space visibility memorandum"
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Final evidence synthesis and verification",
                "step_type": "llm",
                "aim": "Synthesize all retrieved evidence to determine final verification status.",
                "stage_action": (
                    "Read all retrieved passages across all hops and create a comprehensive evidence summary. "
                    "State whether the claim is verified, refuted, or partially verified based on the evidence. "
                    "If verification is incomplete, explicitly list remaining gaps under 'Missing:'."
                ),
                "reasoning_questions": (
                    "1. What is the complete chain of evidence supporting the claim?\n"
                    "2. Are there any contradictions in the evidence?\n"
                    "3. Does the evidence fully cover all claim elements?\n"
                    "4. What is the final verification status and why?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages from all hops:\n"
                    "[Hop1] Apollo 11 | Landed July 20, 1969 with Armstrong and Aldrin\n"
                    "[Hop2a] Moon landing | Armstrong first human on lunar surface\n"
                    "[Hop2b] NASA statement | 'Armstrong was first to step onto the moon'\n"
                    "[Hop3] Historical record | Armstrong descended ladder at 02:56 UTC\n"
                    "Summary: Multiple independent sources confirm Armstrong was first.\n"
                    "Verification: Fully verified. All evidence consistently supports the claim.\n"
                    "Missing: None"
                ),
                "dependencies": [1, 4, 5, 7, 9],
            },
        ],
    }
