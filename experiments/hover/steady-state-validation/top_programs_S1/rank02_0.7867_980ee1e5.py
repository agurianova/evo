def entrypoint():
    return {
        "system_prompt": "You are an evidence specialist for claim verification. Your task is to systematically gather evidence from Wikipedia to verify or refute a claim. Always focus on the most relevant, credible, and directly supportive or refuting facts. For query generation steps, output ONLY the search query string without any additional text. For summarization steps, clearly identify supporting/refuting evidence, source credibility, and specific gaps in the evidence.",
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
            # Step 2: Summarize first-hop evidence with gap analysis
            {
                "number": 2,
                "title": "Analyze first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key verification-relevant facts and identify evidence gaps.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that directly support or refute the claim. "
                    "Evaluate source credibility and temporal relevance. Summarize the evidence found and specify "
                    "exactly what is still missing to verify the claim."
                ),
                "reasoning_questions": (
                    "What specific facts in the passages directly support or refute the claim? "
                    "Are there any temporal or causal connections that are relevant? "
                    "Which facts are from credible sources (e.g., primary sources, official records)? "
                    "What evidence is still missing to fully verify the claim? (e.g., missing dates, missing parties, missing causal links)"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Passage: '[1] Apollo 11 | Apollo 11 was the spaceflight that first landed humans on the Moon. "
                    "Commander Neil Armstrong and lunar module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on July 20, 1969...'\n"
                    "Relevant fact: The passage states the moon landing occurred in 1969, which directly supports the claim. "
                    "The source (Apollo 11 mission) is a primary source. Missing evidence: Independent verification of the date and whether there were any controversies."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query variant A
            {
                "number": 3,
                "title": "Generate query for evidence aspect A",
                "step_type": "llm",
                "aim": "Generate search query for specific missing evidence aspect (branch A).",
                "stage_action": (
                    "Based on evidence gaps identified, generate a concise search query for one specific missing aspect "
                    "(e.g., dates, key figures, causal events). Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Current evidence: We have confirmed the event happened in 1969 via Apollo 11 mission.\n"
                    "Missing: Verification of the exact date and whether there were any controversies.\n"
                    "Query: 'Apollo 11 moon landing date and conspiracy theories'"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate second-hop query variant B
            {
                "number": 4,
                "title": "Generate query for evidence aspect B",
                "step_type": "llm",
                "aim": "Generate search query for different missing evidence aspect (branch B).",
                "stage_action": (
                    "Based on evidence gaps identified, generate a concise search query for a different missing aspect "
                    "(e.g., if branch A was about dates, branch B about key figures). Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Current evidence: We have confirmed the event happened in 1969 via Apollo 11 mission.\n"
                    "Missing: Verification of the exact date and whether there were any controversies.\n"
                    "Query: 'Neil Armstrong and Buzz Aldrin moon landing roles'"
                ),
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (branch A)
            {
                "number": 5,
                "title": "Retrieve passages for aspect A",
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
                "title": "Retrieve passages for aspect B",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 7: Merge and synthesize evidence
            {
                "number": 7,
                "title": "Integrate evidence and identify gaps",
                "step_type": "llm",
                "aim": "Combine all evidence and specify remaining gaps for third hop.",
                "stage_action": (
                    "Combine first-hop summary with second-hop passages from both branches. Identify all supporting/refuting "
                    "evidence, source credibility, and logical connections. Specify exactly what evidence is still missing."
                ),
                "reasoning_questions": (
                    "What new facts were found in second-hop passages? Do they fill first-hop gaps? "
                    "What specific evidence is still missing? (e.g., independent verification, missing causal links)"
                ),
                "example_reasoning": (
                    "First-hop summary: Confirmed moon landing in 1969 via Apollo 11 mission.\n"
                    "Branch A passages: [1] Apollo 11 | ... landed on July 20, 1969 ... [2] Moon landing conspiracy theories | "
                    "Some claim the landing was faked, but NASA has provided evidence including moon rocks.\n"
                    "Branch B passages: [1] Neil Armstrong | First man on the moon, walked on the surface on July 20, 1969.\n"
                    "Integrated: The date (July 20, 1969) is confirmed by multiple sources including Armstrong's role. "
                    "Conspiracy theories addressed by NASA evidence. Missing: Independent scientific verification of moon rocks."
                ),
                "dependencies": [2, 5, 6],
            },
            # Step 8: Generate third-hop query
            {
                "number": 8,
                "title": "Generate final query",
                "step_type": "llm",
                "aim": "Generate search query for most critical remaining evidence gap.",
                "stage_action": (
                    "Based on integrated evidence, generate a concise search query for the most critical missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Current evidence: Confirmed date (July 20, 1969) and key figures, but missing independent scientific verification of moon rocks.\n"
                    "Query: 'Independent verification of Apollo 11 moon rocks'"
                ),
                "dependencies": [7],
            },
            # Step 9: Third-hop retrieval (deep)
            {
                "number": 9,
                "title": "Retrieve final passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }
