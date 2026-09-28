def entrypoint():
    return {
        "system_prompt": "You are a fact-checker verifying claims via multi-hop evidence retrieval. Your goal is to find all relevant evidence to verify the claim. Maximize recall, even at cost of precision.",
        "steps": [
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
            {
                "number": 2,
                "title": "Filter and summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Filter the first-hop passages for relevance to the claim and summarize key evidence.",
                "stage_action": (
                    "Remove only clearly irrelevant passages; keep borderline ones that might be tangentially related. "
                    "Then, summarize the remaining passages into a concise evidence summary."
                ),
                "reasoning_questions": (
                    "Which passages directly support or refute the claim? "
                    "What are the key facts from these passages?"
                ),
                "example_reasoning": (
                    "Passage [1] discusses X which is irrelevant. "
                    "Passage [2] states Y which directly supports the claim. "
                    "Summary: The claim is partially supported by Y."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a broad search query for the first second-hop.",
                "stage_action": (
                    "Based on the evidence summary, determine what additional evidence is needed to fully verify the claim. "
                    "Write a concise search query for the missing evidence. Use synonyms and related terms to broaden the query "
                    "(e.g., 'location, place, site of [event]'). Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing? "
                    "Which entities or relationships need further exploration?"
                ),
                "example_reasoning": (
                    "The summary shows the claim about event date is supported, but the location is missing. "
                    "Query: location, place, site of [event]."
                ),
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after first second-hop and generate a broad search query.",
                "stage_action": (
                    "Based on the first-hop summary and first second-hop retrieval results, determine what additional evidence is still missing. "
                    "Write a concise search query for the missing evidence. Use synonyms and related terms to broaden the query. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact remains missing after first second-hop? "
                    "Which part of the claim is still unverified?"
                ),
                "example_reasoning": (
                    "The first second-hop provided location, but the cause is missing. "
                    "Query: cause, reason, origin of [event]."
                ),
                "dependencies": [2, 4],
            },
            {
                "number": 6,
                "title": "Retrieve second second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Filter and integrate second-hop evidence",
                "step_type": "llm",
                "aim": "Filter both second-hop passages and integrate with first-hop evidence.",
                "stage_action": (
                    "Remove only clearly irrelevant passages from both second-hop retrievals; keep borderline ones. "
                    "Then, combine the relevant evidence from both second-hop retrievals with the first-hop summary "
                    "to create a unified evidence summary."
                ),
                "reasoning_questions": (
                    "Which second-hop passages fill gaps in the first-hop summary? "
                    "How do they connect to the existing evidence?"
                ),
                "example_reasoning": (
                    "Passage [3] provides the location, which was missing. Passage [5] provides the cause. "
                    "Updated summary: The event occurred at [location] due to [cause]."
                ),
                "dependencies": [2, 4, 6],
            },
            {
                "number": 8,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a broad search query for third hop.",
                "stage_action": (
                    "Based on the unified evidence summary, determine if the claim is fully verified or if gaps remain. "
                    "If gaps exist, write a concise search query for the missing evidence (using synonyms and related terms). "
                    "Otherwise, output 'NO HOP NEEDED'. Output ONLY the query or 'NO HOP NEEDED'."
                ),
                "reasoning_questions": (
                    "Is there any part of the claim not supported by evidence? "
                    "What specific fact would complete the verification?"
                ),
                "example_reasoning": (
                    "The summary has location and cause, but the aftermath is missing. "
                    "Query: aftermath, consequence, result of [event]."
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Filter and synthesize final evidence",
                "step_type": "llm",
                "aim": "Produce final evidence summary accounting for potential absence of third-hop evidence.",
                "stage_action": (
                    "If the third-hop query step output 'NO HOP NEEDED', ignore the third-hop retrieval results and use the unified "
                    "evidence summary from step7 as the final summary. Otherwise, remove only clearly irrelevant third-hop passages "
                    "and integrate the relevant ones with the step7 summary to create a final evidence summary."
                ),
                "reasoning_questions": (
                    "Does the third-hop query step indicate no hop was needed? "
                    "Which third-hop passages complete the verification if available?"
                ),
                "example_reasoning": (
                    "Step8 output was 'NO HOP NEEDED', so the final summary is: The event occurred at [location] due to [cause]."
                ),
                "dependencies": [7, 8, 9],
            },
        ],
    }