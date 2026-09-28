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
                "aim": "Extract key facts from initial retrieved passages, identify missing evidence, and generate a comprehensive search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. "
                    "Then, identify the specific information still missing to verify the claim. "
                    "Generate a single search query string that covers multiple angles of the missing evidence using OR combinations (e.g., 'term1 OR term2'). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. What specific information is still missing to verify the claim?\n"
                    "5. What are multiple ways to phrase the query to capture different aspects of the missing information?\n"
                    "6. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Crew | The crew included Neil Armstrong and Buzz Aldrin.\n"
                    "Relevant passages: [1] and [2] provide mission details and crew members.\n"
                    "Key facts: Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.\n"
                    "Missing: Neil Armstrong's role as the first person to step on the moon.\n"
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
                "aim": "Extract key facts from second-hop retrieved passages, identify remaining gaps, and generate a comprehensive search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. "
                    "Then, identify the specific information still missing to verify the claim. "
                    "Generate a single search query string that covers multiple angles of the missing evidence using OR combinations. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence connect to the original claim and previous evidence?\n"
                    "3. What specific information is still missing to verify the claim?\n"
                    "4. What are multiple phrasings to capture the missing information?\n"
                    "5. How can you combine these using OR for maximum recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Previous summary: 'Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.'\n"
                    "Passages:\n"
                    "[1] Moon landing | Neil Armstrong was the first human to step onto the lunar surface.\n"
                    "New evidence: Neil Armstrong was the first to step on the moon.\n"
                    "Missing: Official NASA timestamp of the first step.\n"
                    "NASA Armstrong first step timestamp OR moon landing exact time OR Apollo 11 step time"
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
                "aim": "Synthesize third-hop evidence, identify critical gaps, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. "
                    "Then, identify the specific information still missing to fully verify the claim. "
                    "Generate a single search query string that covers multiple angles of the missing evidence using OR combinations. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What key evidence was found in these passages?\n"
                    "2. How does this evidence complete partial verification?\n"
                    "3. What critical information remains missing?\n"
                    "4. What search terms would capture this final missing piece?\n"
                    "5. How to structure the query for maximum precision and recall?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Previous evidence: Apollo 11 landed on July 20, 1969.\n"
                    "Passages:\n"
                    "[1] Historical records | The Apollo 11 mission concluded on July 24, 1969.\n"
                    "New evidence: Mission concluded in 1969.\n"
                    "Missing: Confirmation that the landing (not just conclusion) occurred in 1969.\n"
                    "Apollo 11 moon landing year OR lunar module landing date 1969 OR moon landing year confirmation"
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
                "aim": "Evaluate fourth-hop evidence completeness and generate final search query if needed.",
                "stage_action": (
                    "Read the retrieved passages and determine if the claim can be fully verified. "
                    "If missing information remains, generate a single search query string covering multiple angles of the gap using OR combinations. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. Does the combined evidence fully verify the claim?\n"
                    "2. If not, what is the single most critical missing piece?\n"
                    "3. What are the most precise search terms for this final gap?\n"
                    "4. How to structure the query to maximize chances of retrieval?"
                ),
                "example_reasoning": (
                    "Claim: 'The Great Wall of China is visible from space.'\n"
                    "Previous evidence: The wall is difficult to see with the naked eye from low Earth orbit.\n"
                    "Passages:\n"
                    "[1] Astronaut reports | Astronauts require binoculars to see the wall clearly.\n"
                    "Critical gap: Official NASA position on wall visibility.\n"
                    "NASA Great Wall visibility statement OR official NASA position on Great Wall OR space visibility of Great Wall"
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Retrieve fifth-hop passages (final evidence)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Final evidence synthesis and verification",
                "step_type": "llm",
                "aim": "Synthesize all retrieved evidence to determine final verification status.",
                "stage_action": (
                    "Read all retrieved passages across all hops and create a comprehensive summary of evidence. "
                    "State whether the claim is verified, refuted, or partially verified based on the evidence. "
                    "If verification is incomplete, explicitly list remaining gaps under 'Missing:'."
                ),
                "reasoning_questions": (
                    "1. What is the complete chain of evidence supporting the claim?\n"
                    "2. Are there any contradictions in the evidence?\n"
                    "3. Does the evidence fully cover all elements of the claim?\n"
                    "4. What is the final verification status and why?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Passages from all hops:\n"
                    "[Hop1] Apollo 11 | Landed on moon July 20, 1969\n"
                    "[Hop2] Mission dates | Launched July 16, landed July 20, returned July 24, 1969\n"
                    "[Hop3] Historical context | Space race concluded successfully in 1969\n"
                    "[Hop4] NASA archives | 'Apollo 11 completed the first manned lunar landing in 1969'\n"
                    "[Hop5] Press coverage | 'Man on the moon, 1969'\n"
                    "Summary: Multiple independent sources confirm the moon landing occurred in 1969.\n"
                    "Verification: Fully verified. All evidence consistently points to 1969 as the year of the moon landing.\n"
                    "Missing: None"
                ),
                "dependencies": [1, 3, 5, 7, 9],
            },
        ],
    }
