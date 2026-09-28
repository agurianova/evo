def entrypoint():
    return {
        "system_prompt": "Query steps (3,6): ONLY search query. Rules: specific entities/dates; step3:5-8w, step6:5-10w; no pronouns. Prioritize accuracy.",
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
                    "3. Summarize the key evidence, balancing factual accuracy with preserving potentially relevant information for query generation. End the summary with a specific verification note that identifies the most critical missing piece for the next hop (second hop)."
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
                    "Summary: Marie Curie was born in Warsaw, Poland, on 7 November 1867. However, one passage claims Paris as birthplace. Note: Verify the correct birthplace city and country to resolve the discrepancy."
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
                    "first iphone public release exact date"
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
                    "3. Resolve any conflicts when possible by prioritizing more detailed information. Explain your resolution.\n"
                    "4. After integration, explicitly identify any remaining evidence gaps that prevent full verification.\n"
                    "   - If multiple gaps are closely related, merge them into a single gap description.\n"
                    "5. Assign priority scores (1-5, 1=highest) to each gap based on criticality for verification using these criteria:\n"
                    "   Priority 1: gap prevents verification (claim cannot be verified without this);\n"
                    "   Priority 2: gap weakens evidence but verification is still possible;\n"
                    "   Priority 3: gap is about a minor detail;\n"
                    "   Priority 4: gap is about context not needed for verification;\n"
                    "   Priority 5: gap is irrelevant.\n"
                    "   If multiple gaps have priority 1, select the single most critical gap (based on direct relevance to the claim) and reassign the others to priority 2 or lower."
                ),
                "reasoning_questions": "What new facts are in the second-hop passages? How do they relate to the first-hop summary? Are there conflicts? How are they resolved? What specific information is still missing? What is the priority score (1-5) for each gap?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released on June 29, 2007 at 6:00 PM EST.\n"
                    "First-hop summary: The iPhone was introduced by Steve Jobs in January 2007, but became available to the public in June 2007. Note: Exact public release date and time are missing.\n"
                    "Second-hop passages:\n"
                    "[0] iPhone | The first iPhone went on sale in the United States on June 29, 2007.\n"
                    "[1] Apple Inc. | ...launched the iPhone in 2007...\n"
                    "New facts: Passage 0 states the exact release date: June 29, 2007, but does not specify the time.\n"
                    "Conflict resolution: None.\n"
                    "Remaining gaps: The exact time of release (6:00 PM EST) is not confirmed by any passage. [Priority: 1]\n"
                    "Comprehensive summary: The first iPhone was released on June 29, 2007, but the exact time (6:00 PM EST) remains unverified."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the highest priority remaining gap and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the comprehensive summary (which includes priority scores), generate a search query for the highest priority gap (score 1). Write a search query that:\n"
                    "- Uses specific entities and dates\n"
                    "- Includes disambiguating context for ambiguous entities\n"
                    "- If the comprehensive summary provides alternative terms for the gap, derive 1-2 synonyms; otherwise, use the original terms.\n"
                    "- Uses domain-specific terminology\n"
                    "- Uses 5-10 words to accommodate expansion\n"
                    "Extra text will break the system. Provide ONLY the search query."
                ),
                "reasoning_questions": "What specific information is still missing? Why critical? How can context-derived synonyms improve recall?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Albert Einstein won the Nobel Prize for his theory of relativity.\n"
                    "Current evidence summary: Einstein won the Nobel Prize in 1921 for the photoelectric effect, not relativity. The official citation is missing. First-hop evidence mentioned 'Nobel Committee' and 'official motivation'.\n"
                    "Remaining gaps: Exact wording of the Nobel Prize citation. [Priority: 1]\n"
                    "Synonym mapping: 'citation' -> 'award motivation' (from evidence summary)\n"
                    "einstein nobel prize committee award motivation official citation"
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
