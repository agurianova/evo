def entrypoint():
    return {
        "system_prompt": "You are an evidence specialist for claim verification. Your task is to systematically gather evidence from Wikipedia to verify or refute a claim. Always focus on the most relevant, credible, and directly supportive or refuting facts while maximizing breadth of evidence coverage to capture all potential supporting documents. For query generation steps, output ONLY the search query string without any additional text. For summarization steps, clearly identify supporting/refuting evidence, source credibility, specific gaps in the evidence, and note any overlapping evidence across branches.",
        "steps": [
            # Step 1: First-hop retrieval (k=7 for precision)
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
            # Step 2: Summarize first-hop evidence with flexible gap analysis
            {
                "number": 2,
                "title": "Analyze first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key verification-relevant facts, categorize evidence gaps, and identify source credibility.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that directly support or refute the claim. "
                    "Evaluate source credibility and temporal relevance. Summarize the evidence found and specify "
                    "exactly what is still missing to verify the claim, categorizing each gap by a meaningful type "
                    "that is specific to the claim (e.g., temporal, causal, entity, or any other appropriate category)."
                ),
                "reasoning_questions": (
                    "What specific facts in the passages directly support or refute the claim? "
                    "Are there any temporal or causal connections that are relevant? "
                    "Which facts are from credible sources (e.g., primary sources, official records)? "
                    "What evidence is still missing to fully verify the claim? Categorize each gap by a meaningful type "
                    "specific to the claim (e.g., temporal, causal, entity, or custom category), and explain why it is critical."
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Passage: '[1] Apollo 11 | Apollo 11 was the spaceflight that first landed humans on the Moon. "
                    "Commander Neil Armstrong and lunar module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on July 20, 1969...\n'"
                    "Relevant fact: The passage states the moon landing occurred in 1969, which directly supports the claim. "
                    "The source (Apollo 11 mission) is a primary source. Missing evidence: \n"
                    "- Temporal: Independent verification of the exact date (July 20, 1969)\n"
                    "- Causal: Evidence addressing conspiracy theories about the event's authenticity\n"
                    "- Entity: Roles of key figures beyond Armstrong and Aldrin"
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
                    "Missing: Temporal: Independent verification of exact date; Causal: Evidence addressing conspiracy theories.\n"
                    "Query: 'Apollo 11 moon landing independent date verification'"
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
                    "Missing: Temporal: Independent verification of exact date; Causal: Evidence addressing conspiracy theories.\n"
                    "Query: 'Moon landing conspiracy theories scientific rebuttals'"
                ),
                "dependencies": [2],
            },
            # Step 5: Generate second-hop query variant C (new branch)
            {
                "number": 5,
                "title": "Generate query for evidence aspect C",
                "step_type": "llm",
                "aim": "Generate search query for third distinct missing evidence aspect (branch C).",
                "stage_action": (
                    "Based on evidence gaps identified, generate a concise search query for a third distinct missing aspect "
                    "(e.g., physical evidence, independent verification). Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Current evidence: We have confirmed the event happened in 1969 via Apollo 11 mission.\n"
                    "Missing: Temporal: Independent verification of exact date; Causal: Evidence addressing conspiracy theories.\n"
                    "Query: 'Apollo 11 moon rocks independent laboratory analysis'"
                ),
                "dependencies": [2],
            },
            # Step 6: Second-hop retrieval (branch A)
            {
                "number": 6,
                "title": "Retrieve passages for aspect A",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 7: Second-hop retrieval (branch B)
            {
                "number": 7,
                "title": "Retrieve passages for aspect B",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 8: Second-hop retrieval (branch C)
            {
                "number": 8,
                "title": "Retrieve passages for aspect C",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            # Step 9: Integrate evidence and generate critical query
            {
                "number": 9,
                "title": "Integrate evidence and generate query",
                "step_type": "llm",
                "aim": "Combine all evidence, identify/rank gaps by criticality, and generate query for most critical gap.",
                "stage_action": (
                    "Read all retrieved passages from first hop (step1) and second hop branches (steps6,7,8). "
                    "Identify all supporting and refuting evidence, evaluate source credibility, and note logical connections. "
                    "Explicitly state when evidence overlaps across branches. Categorize each remaining evidence gap by a meaningful type "
                    "(specific to the claim) and rank them by criticality (how essential is filling this gap to verifying the claim?). "
                    "Generate a concise search query targeting the most critical gap. Output ONLY the search query string without any additional text."
                ),
                "reasoning_questions": (
                    "What new facts were found in second-hop passages? Do they fill any first-hop gaps? "
                    "Which evidence appears in multiple branches (overlap)? What specific evidence is still missing? "
                    "Categorize each gap by a meaningful type (e.g., temporal, causal, entity, or custom category) and explain criticality. "
                    "Which gap is the most critical to verify the claim, and why? Generate a search query for that gap."
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "First-hop passages: [1] Apollo 11 | Apollo 11 was the spaceflight that first landed humans on the Moon. "
                    "Commander Neil Armstrong and lunar module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on July 20, 1969...\n"
                    "Second-hop branch A: [1] July 20, 1969 | The date is confirmed by NASA mission logs and radio transcripts.\n"
                    "Second-hop branch B: [1] Moon landing conspiracy theories | Claims of fakery debunked by scientific evidence.\n"
                    "Second-hop branch C: [1] Moon rocks | Analysis confirms extraterrestrial origin.\n"
                    "Analysis:\n"
                    "- Supporting evidence: Date (July 20, 1969) confirmed by first-hop and branch A.\n"
                    "- Overlap: Conspiracy theory rebuttals appear in branch B and first-hop passage [2] (if available).\n"
                    "- Gaps:\n"
                    "   * Gap 1 (Category: Independent Verification): No non-NASA verification of landing date. Criticality: High (core to claim).\n"
                    "   * Gap 2 (Category: Physical Evidence): Missing independent analysis of moon rocks. Criticality: High.\n"
                    "   * Gap 3 (Category: Key Participants): Roles of other astronauts (e.g., Michael Collins) unclear. Criticality: Medium.\n"
                    "Most critical gap: Gap 1 (Independent Verification) is most critical for verifying the claim's core assertion.\n"
                    "Query: 'Independent verification of Apollo 11 moon landing date'"
                ),
                "dependencies": [1, 6, 7, 8],
            },
            # Step 10: Final retrieval (deep)
            {
                "number": 10,
                "title": "Retrieve final passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }
