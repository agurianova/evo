def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Always follow instructions precisely. For query generation steps, output ONLY the search query string with no additional text, formatting, or explanations.",
        "steps": [
            {
                "number": 1,
                "title": "Initial evidence retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Generate direct evidence query",
                "step_type": "llm",
                "aim": "Extract key facts directly supporting or refuting the claim from initial passages and generate focused search query for direct evidence.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly prove or disprove the claim. "
                    "Focus on explicit statements about the claim's subject and predicate. "
                    "Generate a single search query string that uses OR combinations to cover multiple phrasings of the direct evidence (e.g., 'term1 OR term2'). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which passages contain explicit statements about the claim's subject and predicate?\n"
                    "3. What are the key facts from these passages that directly support or refute the claim?\n"
                    "4. What specific information is still missing for direct verification?\n"
                    "5. What are multiple ways to phrase the query to capture different aspects of the missing direct evidence?\n"
                    "6. How can you combine these phrases using OR to maximize recall for direct evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Crew | The crew included Neil Armstrong and Buzz Aldrin.\n"
                    "Direct evidence passages: None explicitly state Armstrong was first.\n"
                    "Key facts: Mission details and crew members, but missing Armstrong's role as first.\n"
                    "Missing: Direct statement that Neil Armstrong was the first person to step on the moon.\n"
                    "Neil Armstrong first person moon landing OR Neil Armstrong first step on moon OR first human on moon Armstrong"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve direct evidence passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate contextual evidence query",
                "step_type": "llm",
                "aim": "Identify contextual or background information that might indirectly support the claim from initial passages and generate query for contextual evidence.",
                "stage_action": (
                    "Read the retrieved passages and identify contextual information that provides background, historical setting, or related events. "
                    "Focus on information that, when combined with common knowledge, strengthens the claim. "
                    "Generate a single search query string that uses OR combinations to cover multiple contextual angles (e.g., 'context1 OR context2'). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which passages provide background, historical context, or related events?\n"
                    "3. How does this contextual information indirectly support the claim?\n"
                    "4. What specific contextual information is still missing to build a stronger case?\n"
                    "5. What are multiple ways to phrase the query to capture different contextual angles?\n"
                    "6. How can you combine these phrases using OR to maximize recall for contextual evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Crew | The crew included Neil Armstrong and Buzz Aldrin.\n"
                    "Contextual passages: [1] provides the mission date, [2] provides crew members.\n"
                    "Indirect support: Knowing the mission date and crew helps establish the setting, but doesn't directly state who was first.\n"
                    "Missing: Context about the sequence of events during the moon landing (e.g., who exited the module first).\n"
                    "Apollo 11 moon landing sequence OR who exited lunar module first OR Armstrong Aldrin moon landing order"
                ),
                "dependencies": [1],
            },
            {
                "number": 5,
                "title": "Retrieve contextual evidence passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Merge evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Synthesize evidence from all retrieved passages, identify remaining gaps, and generate comprehensive search query for next hop.",
                "stage_action": (
                    "Read all retrieved passages from initial hop and both branches. Create concise summary of all relevant facts. "
                    "Identify specific information still missing to verify the claim. "
                    "Generate a single search query string that covers multiple angles of missing evidence using OR combinations. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. What evidence was found in the initial hop, direct branch, and contextual branch?\n"
                    "3. How do these pieces of evidence connect to form a chain of verification?\n"
                    "4. What specific information is still missing to complete the verification?\n"
                    "5. What are multiple phrasings to capture the missing information?\n"
                    "6. How can you combine these using OR for maximum recall?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Initial hop passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Mission duration | The mission lasted from July 16 to July 24, 1969.\n"
                    "Direct branch passages:\n"
                    "[1] Historical record | The lunar module touched down at 20:17 UTC on July 20, 1969.\n"
                    "Contextual branch passages:\n"
                    "[1] Space race | The Apollo program achieved the moon landing goal set by President Kennedy in the 1960s.\n"
                    "Summary: The mission occurred in July 1969, and the program was part of the 1960s space race.\n"
                    "Missing: Explicit statement that the landing (not just the mission) occurred in 1969.\n"
                    "Apollo 11 moon landing year confirmation OR lunar module landing date 1969 OR moon landing year official record"
                ),
                "dependencies": [1, 3, 5],
            },
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
            {
                "number": 8,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Synthesize evidence from all retrieved passages, identify critical gaps, and generate precise search query for next hop.",
                "stage_action": (
                    "Read all retrieved passages and create a concise summary of relevant facts. "
                    "Identify the specific information still missing to fully verify the claim. "
                    "Generate a single search query string that covers multiple angles of the missing evidence using OR combinations. "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What key evidence was found in all passages?\n"
                    "2. How does this evidence complete partial verification?\n"
                    "3. What critical information remains missing?\n"
                    "4. What search terms would capture this final missing piece?\n"
                    "5. How to structure the query for maximum precision and recall?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Previous evidence: Apollo 11 landed on July 20, 1969.\n"
                    "Passages from all hops:\n"
                    "[1] Historical records | The Apollo 11 mission concluded on July 24, 1969.\n"
                    "New evidence: Mission concluded in 1969.\n"
                    "Missing: Confirmation that the landing (not just conclusion) occurred in 1969.\n"
                    "Apollo 11 moon landing year OR lunar module landing date 1969 OR moon landing year confirmation"
                ),
                "dependencies": [1, 3, 5, 7],
            },
            {
                "number": 9,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Final evidence synthesis and verification",
                "step_type": "llm",
                "aim": "Synthesize all retrieved evidence to determine final verification status and identify remaining gaps.",
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
                    "[Hop1] Mission dates | Launched July 16, landed July 20, returned July 24, 1969\n"
                    "[Hop2] Historical record | Lunar module touched down July 20, 1969\n"
                    "[Hop3] Space race | Apollo program achieved goal in 1960s\n"
                    "[Hop4] NASA archives | 'Apollo 11 completed the first manned lunar landing in 1969'\n"
                    "Summary: Multiple independent sources confirm the moon landing occurred in 1969.\n"
                    "Verification: Fully verified. All evidence consistently points to 1969 as the year of the moon landing.\n"
                    "Missing: None"
                ),
                "dependencies": [1, 3, 5, 7, 9],
            },
        ],
    }
