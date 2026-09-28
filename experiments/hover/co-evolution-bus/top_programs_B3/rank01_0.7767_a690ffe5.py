def entrypoint():
    return {
        "system_prompt": "Fact-checker: In query steps (3,6), output ONLY the query. In summarization, extract facts and resolve conflicts with primary sources/dates.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "1. Extract key facts from the retrieved passages that are directly relevant to the claim.\n"
                    "2. Note any conflicts between the passages regarding these facts (do not resolve conflicts yet).\n"
                    "3. Summarize the key evidence found, including any noted conflicts."
                ),
                "reasoning_questions": "What key facts support or refute the claim? Are there conflicting facts? If so, what are they?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in January 2007.\n"
                    "Passages:\n"
                    "[1] iPhone | Apple's iPhone was introduced by Steve Jobs in January 2007.\n"
                    "[2] iPhone | The first iPhone went on sale to the public on June 29, 2007.\n"
                    "Relevant facts: Passage 1 states introduction in January 2007; passage 2 states public sale on June 29, 2007.\n"
                    "Conflicts: The claim says 'released', but passage 1 says 'introduced' (not public release).\n"
                    "Summary: The iPhone was introduced in January 2007 but released to the public on June 29, 2007."
                ),
                "dependencies": [1],
                "frozen": False,
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, identify the single most critical missing piece of information needed to verify the claim. "
                    "Formulate a concise, entity-focused search query for that information. "
                    "YOUR ENTIRE RESPONSE MUST BE THE SEARCH QUERY STRING AND NOTHING ELSE. "
                    "DO NOT INCLUDE ANY EXPLANATION, PUNCTUATION, OR ADDITIONAL TEXT. "
                    "ANY EXTRA TEXT WILL CAUSE THE RETRIEVAL SYSTEM TO FAIL."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2],
                "frozen": False,
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
                "frozen": True,
            },
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "1. Extract key facts from the second-hop passages (step 4 output) relevant to the claim.\n"
                    "2. Integrate these new facts with the first-hop evidence summary (step 2 output) to create a comprehensive evidence summary.\n"
                    "3. Resolve any conflicts by prioritizing primary sources and checking publication dates. Explain your resolution."
                ),
                "reasoning_questions": "What new facts are in the second-hop passages? How do they relate to the first-hop summary? Are there conflicts? How are they resolved using primary sources/dates?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Albert Einstein won the Nobel Prize for his theory of relativity.\n"
                    "First-hop summary: Einstein won the Nobel Prize in Physics in 1921.\n"
                    "Second-hop passages:\n"
                    "[1] Albert Einstein | awarded the Nobel Prize in Physics in 1921 for... photoelectric effect.\n"
                    "[2] Theory of relativity | not cited in the Nobel Prize award.\n"
                    "Relevant new facts: Prize was for photoelectric effect, not relativity.\n"
                    "Conflict: Claim states prize was for relativity.\n"
                    "Resolution: Primary source (Nobel announcement) states reason.\n"
                    "Comprehensive summary: Einstein won 1921 Nobel Prize for photoelectric effect, not relativity. Claim is false."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the comprehensive evidence summary, identify the final critical missing piece of information needed to verify the claim. "
                    "Formulate a precise search query for that information. "
                    "This is the final retrieval (step 7) which uses a deep search (k=10), so make the query very precise to maximize relevant results. "
                    "YOUR ENTIRE RESPONSE MUST BE THE SEARCH QUERY STRING AND NOTHING ELSE. "
                    "DO NOT INCLUDE ANY EXPLANATION, PUNCTUATION, OR ADDITIONAL TEXT. "
                    "ANY EXTRA TEXT WILL CAUSE THE RETRIEVAL SYSTEM TO FAIL."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [5],
                "frozen": False,
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
                "frozen": True,
            },
        ],
    }
