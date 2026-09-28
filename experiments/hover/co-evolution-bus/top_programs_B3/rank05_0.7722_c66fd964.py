def entrypoint():
    return {
        "system_prompt": "Query steps (3,6): ONLY search query. Rules: specific entities/dates, 5-8 words (step 6: 5-10), no pronouns, disambiguate. Prioritize recall while maintaining relevance",
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
                "aim": "Extract key facts and identify prioritized evidence gaps from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "1. Identify facts in the retrieved passages that are directly relevant to the claim.\n"
                    "2. If there are conflicting facts, note the conflict without resolution.\n"
                    "3. Summarize the key evidence, balancing factual accuracy with preserving potentially relevant information for query generation.\n"
                    "4. After the summary, explicitly identify any evidence gaps that prevent full verification and assign priority scores (1-5, where 1=highest) to each gap based on criticality for claim verification.\n"
                    "5. For the highest priority gap (score=1), note 1-2 alternative terms or synonyms that might be used in documents (if applicable)."
                ),
                "reasoning_questions": "What key facts support or refute the claim? Are there conflicts? If so, what are they (without resolution)? What information might seed future queries? What evidence gaps exist and what are their priority scores? For the top gap, what alternative terms might be used in documents?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Marie Curie was born in Paris.\n"
                    "Retrieved passages:\n"
                    "[0] Marie Curie | Born Maria Salomea Skłodowska in Warsaw, Poland, on 7 November 1867...\n"
                    "[1] Paris | ...birthplace of Marie Curie...\n"
                    "Key facts: Marie Curie was born in Warsaw, Poland, on 7 November 1867 (per passage 0). Passage 1 states Paris as birthplace.\n"
                    "Conflict: Two passages give different birthplaces (Warsaw vs Paris).\n"
                    "Summary: Marie Curie was born in Warsaw, Poland, on 7 November 1867. However, one passage claims Paris as birthplace.\n"
                    "Evidence gaps:\n"
                    "  1 (critical): Correct birthplace city and country.\n"
                    "  2 (less critical): Reason for the discrepancy.\n"
                    "Alternative terms for gap 1: 'place of birth', 'natal city'"
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
                    "Based on the summary with prioritized gaps, generate a search query for the highest priority gap (score=1). If there are no gaps, output the original claim as the query.\n"
                    "Write a search query that:\n"
                    "- Uses specific entities and dates\n"
                    "- Includes disambiguating context for ambiguous entities\n"
                    "- If step2 provided alternative terms for the gap, include 1-2 of them (e.g., 'citation' -> 'award motivation')\n"
                    "- Uses domain-specific terminology\n"
                    "- Uses 5-8 words\n"
                    "Extra text will break the retrieval system. Provide ONLY the search query."
                ),
                "reasoning_questions": "What is the highest priority evidence gap? Why is it critical? How can alternative terms (if provided in step2) improve recall? How can the query be made specific per system rules?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Marie Curie was born in Paris.\n"
                    "First-hop summary: ...\n"
                    "marie curie place of birth"
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
                    "4. After integration, explicitly identify any remaining evidence gaps that prevent full verification.\n"
                    "5. Assign priority scores (1-5, where 1=highest) to each gap based on criticality for claim verification."
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
                    "Gap prioritization: 1) Exact release time (critical for precise verification), 2) Retail locations on launch day (less critical)"
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
                    "Based on the comprehensive summary with prioritized gaps, if there are evidence gaps (priority scores 1-5 exist), generate a search query for the highest priority gap (score=1). Otherwise, output the original claim as the search query.\n"
                    "Write a search query that:\n"
                    "- Uses specific entities and dates\n"
                    "- Includes disambiguating context for ambiguous entities\n"
                    "- Derives 1-2 synonyms from the comprehensive summary (e.g., 'citation' -> 'award motivation')\n"
                    "- Uses domain-specific terminology\n"
                    "- Uses 5-10 words to accommodate expansion\n"
                    "Extra text will break the system. Provide ONLY the search query."
                ),
                "reasoning_questions": "What specific information is still missing? Why critical? How can context-derived synonyms improve recall?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Albert Einstein won the Nobel Prize for his theory of relativity.\n"
                    "Current evidence summary: Einstein won the Nobel Prize in 1921 for the photoelectric effect, not relativity. The official citation is missing. First-hop evidence mentioned 'Nobel Committee' and 'official motivation'. Gap prioritization: 1) Exact wording of the Nobel Prize citation (critical), 2) Year of award ceremony (less critical).\n"
                    "Synonym mapping: 'citation' -> 'award motivation'\n"
                    "einstein nobel prize committee official award motivation"
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
