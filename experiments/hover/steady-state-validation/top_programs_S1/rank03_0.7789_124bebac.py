def entrypoint():
    return {
        "system_prompt": "You are an evidence specialist for claim verification. Your task is to systematically gather evidence from Wikipedia to verify or refute a claim. Always focus on the most relevant, credible, and directly supportive or refuting facts while maximizing breadth of evidence coverage to capture all potential supporting documents. For query generation steps, output ONLY the search query string without any additional text. For summarization steps, clearly identify supporting/refuting evidence, source credibility, specific gaps in the evidence, and note any overlapping evidence across branches.",
        "steps": [
            # Step 1: First-hop retrieval (deep)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence with structured gap analysis
            {
                "number": 2,
                "title": "Analyze first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key verification-relevant facts, categorize evidence gaps, and identify source credibility.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that directly support or refute the claim. "
                    "Evaluate source credibility and temporal relevance. Summarize the evidence found and specify "
                    "exactly what is still missing to verify the claim, categorizing each gap by type "
                    "(temporal, causal, entity, or other relevant category)."
                ),
                "reasoning_questions": (
                    "What specific facts in the passages directly support or refute the claim? "
                    "Are there any temporal or causal connections that are relevant? "
                    "Which facts are from credible sources (e.g., primary sources, official records)? "
                    "What evidence is still missing to fully verify the claim? Categorize each gap by type "
                    "(e.g., temporal: missing dates; causal: missing cause-effect links; entity: missing key participants)."
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Passage: '[1] Apollo 11 | Apollo 11 was the spaceflight that first landed humans on the Moon. "
                    "Commander Neil Armstrong and lunar module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on July 20, 1969...'\n"
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
            # Step 7: Merge and synthesize evidence with overlap detection
            {
                "number": 7,
                "title": "Integrate evidence and identify gaps",
                "step_type": "llm",
                "aim": "Combine all evidence, detect overlaps, categorize gaps, and estimate completeness.",
                "stage_action": (
                    "Combine first-hop summary with second-hop passages from both branches. Identify all supporting/refuting "
                    "evidence, source credibility, and logical connections. Explicitly note when evidence from different branches "
                    "overlaps (e.g., same fact appears in both A and B). Categorize remaining gaps by type (temporal, causal, entity) "
                    "and estimate the percentage of evidence completeness (0-100%). Specify exactly what evidence is still missing."
                ),
                "reasoning_questions": (
                    "What new facts were found in second-hop passages? Do they fill first-hop gaps? "
                    "Which evidence appears in both branches (overlap)? What specific evidence is still missing? "
                    "Categorize gaps by type (temporal, causal, entity). What is the estimated evidence completeness percentage?"
                ),
                "example_reasoning": (
                    "First-hop summary: Confirmed moon landing in 1969 via Apollo 11 mission.\n"
                    "Branch A passages: [1] Apollo 11 | ... landed on July 20, 1969 ... [2] Moon landing conspiracy theories | "
                    "Some claim the landing was faked, but NASA has provided evidence including moon rocks.\n"
                    "Branch B passages: [1] Neil Armstrong | First man on the moon, walked on the surface on July 20, 1969. "
                    "[2] Moon landing conspiracy theories | Scientific analysis confirms moon rocks are extraterrestrial.\n"
                    "Integrated: \n"
                    "- Supporting evidence: Date (July 20, 1969) confirmed by multiple sources (A1, B1). \n"
                    "- Overlap: Conspiracy theory rebuttals appear in both branches (A2, B2). \n"
                    "- Completeness: 85% (date and conspiracy theories addressed, but missing independent verification of moon rocks). \n"
                    "- Remaining gaps: \n"
                    "  * Temporal: Independent verification of exact date (beyond NASA sources)\n"
                    "  * Entity: Analysis of moon rocks by non-NASA laboratories"
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
                    "Current evidence: Confirmed date (July 20, 1969) and addressed conspiracy theories, but missing independent scientific verification of moon rocks.\n"
                    "Completeness: 85%\n"
                    "Query: 'Independent laboratory analysis of Apollo 11 moon rocks'"
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
