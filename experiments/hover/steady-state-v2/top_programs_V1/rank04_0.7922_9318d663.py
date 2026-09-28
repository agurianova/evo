def entrypoint():
    return {
        "system_prompt": "You are a fact-checker verifying claims via multi-hop evidence retrieval. Your goal is to find all relevant evidence to verify the claim.",
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
                "aim": "Filter the first-hop passages for relevance to the claim and summarize the key evidence.",
                "stage_action": (
                    "Remove any passages not directly relevant to the claim. "
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
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, determine what additional evidence is needed "
                    "to fully verify the claim. Write a concise search query for the missing evidence. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing? "
                    "Which entities or relationships need further exploration to verify the claim?"
                ),
                "example_reasoning": (
                    "The summary shows the claim about event date is supported, "
                    "but the location is missing. Query: 'location of [event]'."
                ),
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Filter and integrate second-hop evidence",
                "step_type": "llm",
                "aim": "Filter the second-hop passages for relevance and integrate with first-hop evidence.",
                "stage_action": (
                    "Remove irrelevant second-hop passages. "
                    "Then, combine the relevant second-hop evidence with the first-hop summary "
                    "to create a unified evidence summary."
                ),
                "reasoning_questions": (
                    "Which second-hop passages fill gaps in the first-hop summary? "
                    "How do they connect to the existing evidence?"
                ),
                "example_reasoning": (
                    "Passage [3] provides the location, which was missing. "
                    "Updated summary: The event occurred at [location] on [date]."
                ),
                "dependencies": [2, 4],
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the unified evidence summary, determine what final piece of evidence "
                    "is needed. Write a concise search query. Output ONLY the query."
                ),
                "reasoning_questions": (
                    "What specific fact is still missing? "
                    "Which part of the claim remains unverified?"
                ),
                "example_reasoning": (
                    "The summary has date and location, but the cause is missing. "
                    "Query: 'cause of [event]'."
                ),
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Filter and synthesize third-hop evidence",
                "step_type": "llm",
                "aim": "Filter the third-hop passages and synthesize a complete evidence summary.",
                "stage_action": (
                    "Remove irrelevant third-hop passages. "
                    "Then, integrate the relevant third-hop evidence with the existing unified summary "
                    "to create a final evidence summary covering all hops."
                ),
                "reasoning_questions": (
                    "Which third-hop passages complete the verification? "
                    "How do they fit into the existing narrative?"
                ),
                "example_reasoning": (
                    "Passage [5] states the cause was Z. "
                    "Final summary: The event occurred at [location] on [date] due to Z."
                ),
                "dependencies": [5, 7],
            },
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify if any evidence gaps remain and generate a search query for the fourth hop.",
                "stage_action": (
                    "Based on the final evidence summary, determine if the claim is fully verified "
                    "or if gaps remain. If gaps exist, write a concise search query for the missing evidence. "
                    "Otherwise, output 'NO HOP NEEDED'. Output ONLY the query or 'NO HOP NEEDED'."
                ),
                "reasoning_questions": (
                    "Is there any part of the claim not supported by evidence? "
                    "What specific fact would complete the verification?"
                ),
                "example_reasoning": (
                    "The cause is verified, but the aftermath is missing. "
                    "Query: 'aftermath of [event]'."
                ),
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }