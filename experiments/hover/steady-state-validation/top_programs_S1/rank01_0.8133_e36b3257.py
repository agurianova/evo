def entrypoint():
    return {
        "system_prompt": "You are an evidence specialist for claim verification. Your task is to guide the retrieval of evidence by generating precise search queries and synthesizing evidence with a focus on verification. For query generation steps: output ONLY the search query, nothing else. For synthesis steps: focus on identifying supporting/refuting evidence, temporal alignment, causal connections, and source credibility. Always perform explicit gap analysis after synthesis to identify missing evidence.",
        "steps": [
            # Step 1: First-hop retrieval (broad)
            {
                "number": 1,
                "title": "First-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: First-hop synthesis with verification focus and gap analysis
            {
                "number": 2,
                "title": "First-hop synthesis and gap analysis",
                "step_type": "llm",
                "aim": "Integrate first-hop evidence and identify gaps for further retrieval.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to verifying the claim. "
                    "Focus on supporting/refuting evidence, temporal alignment, and causal connections. "
                    "Then, identify up to two specific gaps in the evidence that prevent full verification."
                ),
                "reasoning_questions": (
                    "1. What specific facts from the passages directly support or refute the claim?\n"
                    "2. Are there temporal inconsistencies between the evidence and the claim?\n"
                    "3. What causal mechanisms are described that link the evidence to the claim?\n"
                    "4. What are the top two missing pieces of evidence needed to verify the claim? (Be specific: e.g., 'evidence about [entity] in [time period]')"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing was faked in 1969.'\n"
                    "Evidence: [Passage 1] NASA archives show photos from Apollo 11. [Passage 2] Astronauts left retroreflectors on the moon.\n"
                    "Analysis:\n"
                    "  - Supporting: Retroreflectors are still used for laser ranging, confirming presence on the moon.\n"
                    "  - Temporal: The photos and retroreflectors are from 1969, matching the claim time.\n"
                    "  - Causal: The retroreflectors require physical placement, which implies a moon landing.\n"
                    "Gaps:\n"
                    "  1. Independent verification of the moon landing by non-NASA entities in 1969.\n"
                    "  2. Evidence of the technology available in 1969 to fake the landing convincingly."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for first gap
            {
                "number": 3,
                "title": "Generate query for first gap",
                "step_type": "llm",
                "aim": "Generate a precise search query to find evidence for the first identified gap.",
                "stage_action": (
                    "Based on the first gap identified in the previous step, write a concise search query "
                    "that will retrieve evidence specifically addressing that gap. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Gap: 'Independent verification of the moon landing by non-NASA entities in 1969.'\n"
                    "Query: '1969 moon landing independent verification Soviet Union'"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate query for second gap (if exists)
            {
                "number": 4,
                "title": "Generate query for second gap",
                "step_type": "llm",
                "aim": "Generate a precise search query to find evidence for the second identified gap (if any).",
                "stage_action": (
                    "If a second gap was identified, write a concise search query for it. "
                    "If no second gap, output 'NO_QUERY'. "
                    "Output ONLY the search query or 'NO_QUERY', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Gap: 'Evidence of the technology available in 1969 to fake the landing convincingly.'\n"
                    "Query: '1969 technology to fake moon landing video'\n\n"
                    "No second gap: 'NO_QUERY'"
                ),
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (branch A)
            {
                "number": 5,
                "title": "Second-hop retrieval (branch A)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Second-hop retrieval (branch B)
            {
                "number": 6,
                "title": "Second-hop retrieval (branch B)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 7: Synthesize all evidence and identify remaining gaps
            {
                "number": 7,
                "title": "Second-hop synthesis and gap analysis",
                "step_type": "llm",
                "aim": "Integrate all evidence gathered so far and identify remaining gaps.",
                "stage_action": (
                    "Combine evidence from the first hop and both second hop branches. "
                    "Extract verification-focused facts (supporting/refuting, temporal, causal). "
                    "Then, identify up to two specific gaps that remain for full verification."
                ),
                "reasoning_questions": (
                    "1. What new evidence from the second hop addresses the previous gaps?\n"
                    "2. What specific facts still support or refute the claim?\n"
                    "3. Are there any remaining temporal or causal inconsistencies?\n"
                    "4. What are the top two missing pieces of evidence needed now? (Be specific)"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing was faked in 1969.'\n"
                    "First-hop evidence: [Passage 1] NASA archives show photos from Apollo 11. [Passage 2] Astronauts left retroreflectors on the moon.\n"
                    "Second-hop evidence (branch A): [Passage 3] Soviet Union tracked Apollo 11 with telescopes.\n"
                    "Second-hop evidence (branch B): [Passage 4] 1969 TV technology could not fake the moon landing video quality.\n"
                    "Analysis:\n"
                    "  - Supporting: Soviet tracking confirms the mission, and 1969 technology was insufficient for faking.\n"
                    "  - Temporal: All evidence is from 1969.\n"
                    "  - Causal: The technology gap makes faking implausible.\n"
                    "Gaps:\n"
                    "  1. Direct testimony from Apollo 11 astronauts about the landing."
                ),
                "dependencies": [1, 5, 6],
            },
            # Step 8: Generate query for top remaining gap
            {
                "number": 8,
                "title": "Generate query for top remaining gap",
                "step_type": "llm",
                "aim": "Generate a search query for the most critical remaining gap.",
                "stage_action": (
                    "Based on the gap analysis, write a concise search query for the most critical gap. "
                    "If no gaps remain, output 'NO_QUERY'. "
                    "Output ONLY the search query or 'NO_QUERY', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Gap: 'Direct testimony from Apollo 11 astronauts about the landing.'\n"
                    "Query: 'Apollo 11 astronauts moon landing testimony'\n\n"
                    "No gaps: 'NO_QUERY'"
                ),
                "dependencies": [7],
            },
            # Step 9: Third-hop retrieval
            {
                "number": 9,
                "title": "Third-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }
