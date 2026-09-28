def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. For query steps (3,6): output ONLY the search query. Rules: 1) Specific entities & dates 2) 5-8 words 3) Avoid pronouns; disambiguate ambiguous entities. For summarization: step 2 preserves potentially relevant facts without conflict resolution; step 5 resolves conflicts when possible and explicitly identifies remaining gaps. Prioritize accuracy.",
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
                    "1. Identify facts in the retrieved passages that are directly relevant to the claim.\n"
                    "2. If there are conflicting facts, note the conflict without resolution.\n"
                    "3. Summarize the key evidence, balancing factual accuracy with preserving potentially relevant information for query generation."
                ),
                "reasoning_questions": "What key facts support or refute the claim? Are there conflicts? If so, what are they (without resolution)? What information might seed future queries?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Marie Curie was born in Paris.\n"
                    "Retrieved passages:\n"
                    "[0] Marie Curie | Born Maria Salomea Skłodowska in Warsaw, Poland, on 7 November 1867...\n"
                    "[1] Paris | ...birthplace of Marie Curie...\n"
                    "Key facts: Marie Curie was born in Warsaw, Poland (per passage 0). Passage 1 states Paris as birthplace.\n"
                    "Conflict: Two passages give different birthplaces (Warsaw vs Paris).\n"
                    "Summary: Marie Curie was born in Warsaw, Poland, on 7 November 1867. However, one passage claims Paris as birthplace. Note: This discrepancy suggests verifying 'Marie Curie birthplace' to resolve the conflict."
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
                    "Based on the summary, determine what additional evidence is needed to fully verify the claim. Write a concise search query for the missing evidence.\n"
                    "Remember: Follow system query rules (specific entities, dates, 5-8 words, no pronouns, disambiguate).\n"
                    "Extra text will break the retrieval system. Provide ONLY the search query."
                ),
                "reasoning_questions": "What specific information is still missing? Why is it critical for verification? How can the query be made specific per system rules?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in 2007.\n"
                    "First-hop summary: The iPhone was introduced by Steve Jobs in January 2007, but became available to the public in June 2007. Note: Exact public release date (day of month) is missing.\n"
                    "first iphone public release date"
                ),
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
                    "1. Extract key facts from the second-hop passages relevant to the claim.\n"
                    "2. Integrate with the first-hop summary.\n"
                    "3. Resolve any conflicts when possible by prioritizing primary sources and checking publication dates. Explain your resolution.\n"
                    "4. After integration, explicitly identify any remaining evidence gaps that prevent full verification."
                ),
                "reasoning_questions": "What new facts are in the second-hop passages? How do they relate to the first-hop summary? Are there conflicts? How are they resolved? What specific information is still missing?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released on June 29, 2007 at 6:00 PM EST.\n"
                    "First-hop summary: The iPhone was introduced by Steve Jobs in January 2007, but became available to the public in June 2007. Note: Exact public release date and time are missing.\n"
                    "Second-hop passages:\n"
                    "[0] iPhone | The first iPhone went on sale in the United States on June 29, 2007.\n"
                    "[1] Apple Inc. | ...launched the iPhone in 2007...\n"
                    "New facts: Passage 0 states the exact release date: June 29, 2007, but does not specify the time.\n"
                    "Conflict resolution: None.\n"
                    "Remaining gaps: The exact time of release (6:00 PM EST) is not confirmed by any passage.\n"
                    "Comprehensive summary: The first iPhone was released on June 29, 2007, but the exact time (6:00 PM EST) remains unverified."
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
                    "Based on the comprehensive summary and identified gaps, determine the final missing evidence needed. Write a search query that:\n"
                    "- Uses specific entities and dates (per system rules)\n"
                    "- For ambiguous entities, includes disambiguating context\n"
                    "- Includes 1-2 key synonyms to avoid being too narrow\n"
                    "- Uses domain-specific terminology to maximize relevant results in deep search\n"
                    "Extra text will break the retrieval system. Provide ONLY the search query."
                ),
                "reasoning_questions": "What specific information is still missing? Why is it critical? How can query expansion and domain terms improve recall?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Albert Einstein won the Nobel Prize for his theory of relativity.\n"
                    "Current evidence summary: Einstein won the Nobel Prize in 1921, but it was specifically for the photoelectric effect, not relativity. The official citation is missing.\n"
                    "Remaining gaps: The exact wording of the Nobel Prize citation for Einstein.\n"
                    "einstein nobel prize citation photoelectric effect"
                ),
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
