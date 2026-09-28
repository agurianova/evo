def entrypoint():
    return {
        "system_prompt": (
            "You are a meticulous fact-checker verifying claims using multi-hop evidence retrieval. "
            "Your goal is to retrieve all relevant evidence to verify the claim by performing necessary retrieval hops. "
            "When generating a search query, output ONLY the search query string with no additional text. "
            "When analyzing evidence, focus on specific numbers, dates, names, and direct quotes to identify missing information."
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information from first-hop evidence and generate search query for second hop.",
                "stage_action": (
                    "Based on the first-hop retrieved passages, determine what specific information is still missing "
                    "to verify the claim. Write a concise search query to find the missing evidence. "
                    "Output ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific facts are established by the first-hop evidence?\n"
                    "2. What specific information is still missing to verify the claim?\n"
                    "3. Are there any contradictions in the evidence that need resolution?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Retrieved passages:\n"
                    "  [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  [2] Paris landmarks | The Eiffel Tower was constructed between 1887 and 1889.\n"
                    "Analysis: The year 1887 is mentioned as the start year, but we need to confirm if that is when physical construction began.\n"
                    "Eiffel Tower actual construction start date\n\n"
                    "Edge case example (contradictory evidence):\n"
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Retrieved passages:\n"
                    "  [1] Apollo 11 | The lunar module landed on the moon on July 20, 1969.\n"
                    "  [2] Space history | NASA's Apollo 11 mission landed on the moon in 1969.\n"
                    "  [3] Conspiracy theories | Some claim the moon landing was faked in 1969.\n"
                    "Analysis: The conspiracy passage doesn't contradict the event year; primary sources confirm 1969.\n"
                    "NO_HOP_NEEDED"
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
            # Step 4: Integrate first two hops and generate third-hop query
            {
                "number": 4,
                "title": "Integrate first two hops and generate third-hop query",
                "step_type": "llm",
                "aim": "Combine evidence from first two hops and determine if additional evidence is needed.",
                "stage_action": (
                    "Read the first-hop and second-hop retrieved passages. Answer:\n"
                    "- What specific facts have been established?\n"
                    "- What specific information is still missing to verify the claim?\n"
                    "If there is missing information, write a concise search query to find it. \n"
                    "If the evidence is sufficient, output exactly: 'NO_HOP_NEEDED'.\n"
                    "Output ONLY the query or 'NO_HOP_NEEDED' with no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific facts are established by the first-hop evidence?\n"
                    "2. What specific facts are established by the second-hop evidence?\n"
                    "3. Do the two sets of evidence agree, or is there a contradiction?\n"
                    "4. What specific piece of information is still missing?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop passages:\n"
                    "  [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  [2] Paris landmarks | The Eiffel Tower was constructed between 1887 and 1889.\n"
                    "Second-hop passages:\n"
                    "  [1] Gustave Eiffel | In January 1887, Eiffel signed the contract.\n"
                    "  [2] Construction timeline | Groundwork started in late January 1887.\n"
                    "Analysis: Evidence consistently shows construction began in 1887. No missing information.\n"
                    "NO_HOP_NEEDED\n\n"
                    "Edge case example (contradictory evidence):\n"
                    "Claim: 'Water boils at 100 degrees Celsius at sea level.'\n"
                    "First-hop passages:\n"
                    "  [1] Boiling point | Water boils at 100°C at standard atmospheric pressure.\n"
                    "  [2] Chemistry basics | The boiling point of water is 100 degrees Celsius.\n"
                    "Second-hop passages:\n"
                    "  [1] High altitude cooking | Water boils below 100°C at higher elevations.\n"
                    "  [2] Thermodynamics | Boiling point varies with atmospheric pressure.\n"
                    "Analysis: The claim specifies 'at sea level', and first-hop evidence confirms 100°C. Second-hop explains variation but doesn't contradict sea-level condition.\n"
                    "NO_HOP_NEEDED"
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
            # Step 6: Integrate first three hops and generate fourth-hop query
            {
                "number": 6,
                "title": "Integrate first three hops and generate fourth-hop query",
                "step_type": "llm",
                "aim": "Combine evidence from first three hops and determine if additional evidence is needed.",
                "stage_action": (
                    "Read the first-hop, second-hop, and third-hop retrieved passages. Answer:\n"
                    "- What specific facts have been established?\n"
                    "- What specific information is still missing to verify the claim?\n"
                    "If there is missing information, write a concise search query to find it. \n"
                    "If the evidence is sufficient, output exactly: 'NO_HOP_NEEDED'.\n"
                    "Output ONLY the query or 'NO_HOP_NEEDED' with no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific facts are established by the first-hop evidence?\n"
                    "2. What specific facts are established by the second-hop evidence?\n"
                    "3. What specific facts are established by the third-hop evidence?\n"
                    "4. What specific piece of information is still missing?"
                ),
                "example_reasoning": (
                    "Claim: 'Photosynthesis produces oxygen.'\n"
                    "First-hop passages:\n"
                    "  [1] Photosynthesis | Plants convert carbon dioxide and water into glucose and oxygen.\n"
                    "  [2] Biology | The process of photosynthesis releases oxygen as a byproduct.\n"
                    "Second-hop passages:\n"
                    "  [1] Plant physiology | Oxygen is generated during the light-dependent reactions.\n"
                    "  [2] Environmental science | Photosynthesis is the primary source of atmospheric oxygen.\n"
                    "Third-hop passages:\n"
                    "  [1] Biochemistry | The oxygen produced comes from water molecules, not CO2.\n"
                    "  [2] Scientific studies | Oxygen evolution is measured in photosynthetic organisms.\n"
                    "Analysis: All evidence consistently confirms oxygen production. No missing information.\n"
                    "NO_HOP_NEEDED\n\n"
                    "Edge case example (insufficient evidence):\n"
                    "Claim: 'Vitamin C prevents the common cold.'\n"
                    "First-hop passages:\n"
                    "  [1] Nutrition | Vitamin C supports immune function.\n"
                    "  [2] Health | Some studies show reduced cold duration with vitamin C.\n"
                    "Second-hop passages:\n"
                    "  [1] Medical research | Vitamin C does not prevent colds in the general population.\n"
                    "  [2] Clinical trials | No significant reduction in cold incidence was found.\n"
                    "Third-hop passages:\n"
                    "  [1] Cochrane review | Vitamin C supplementation does not prevent colds.\n"
                    "  [2] Public health | Focus should be on handwashing for prevention.\n"
                    "Analysis: Evidence consistently shows vitamin C does not prevent colds. However, the claim specifically says 'prevents', and evidence refutes this. No missing information for verification.\n"
                    "NO_HOP_NEEDED"
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