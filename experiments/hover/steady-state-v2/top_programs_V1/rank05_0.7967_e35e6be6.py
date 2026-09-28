def entrypoint():
    return {
        "system_prompt": "You are an expert evidence specialist for claim verification. Your task is to guide a multi-hop retrieval process to gather all evidence needed to verify a claim. Be precise and concise. When asked for a search query, output ONLY the query string with no additional text.",
        "steps": [
            # Step 1: First-hop retrieval with higher recall
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
            # Step 2: Summarize first-hop evidence with example
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify the most important facts that relate to the claim. "
                    "Produce a concise summary of the evidence found."
                ),
                "reasoning_questions": "What are the central facts directly supporting or contradicting the claim?",
                "example_reasoning": "Example: The claim is about the cause of World War I. Passages mention the assassination of Archduke Franz Ferdinand. Summary: 'The assassination of Archduke Franz Ferdinand by Gavrilo Princip in 1914 is widely regarded as the immediate cause of World War I'",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query with strict output format
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary, determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What key aspect of the claim remains unverified by the current evidence?",
                "example_reasoning": "Example: Summary states the assassination was the immediate cause. Query: 'long term causes of world war i'",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval
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
            # Step 5: Summarize second-hop evidence (fixes inefficient flow)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the missing information.",
                "stage_action": (
                    "Read the second-hop retrieved passages and identify facts that address the missing information from the first hop. "
                    "Produce a concise summary of the new evidence."
                ),
                "reasoning_questions": "How does this new evidence connect to the gaps identified in the first-hop summary?",
                "example_reasoning": "Example: Passages discuss militarism and alliances. Summary: 'Long-term causes of World War I include the arms race (militarism) and complex alliance systems among European powers'",
                "dependencies": [4],
            },
            # Step 6: Combine evidence and enumerate gaps (critical fix)
            {
                "number": 6,
                "title": "Combine evidence and identify gaps",
                "step_type": "llm",
                "aim": "Integrate evidence from first two hops and explicitly enumerate remaining verification gaps.",
                "stage_action": (
                    "Combine the first-hop evidence summary and the second-hop evidence summary. "
                    "List all verified facts, then enumerate any remaining gaps in the evidence that prevent full verification of the claim."
                ),
                "reasoning_questions": "What aspects of the claim are still unverified? Which gap is most critical to resolve?",
                "example_reasoning": "Example: Verified: Immediate cause was assassination; long-term causes include militarism and alliances. Gaps: How did the alliance system specifically lead to global war? What was imperialism's role?",
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query with example
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate a search query to address the most critical remaining gap.",
                "stage_action": (
                    "Based on the enumerated gaps, select the most critical gap and write a concise search query to find evidence for it.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "Which gap has the highest impact on claim verification?",
                "example_reasoning": "Example: Gap: role of imperialism. Query: 'imperialism role in world war i'",
                "dependencies": [6],
            },
            # Step 8: Third-hop retrieval with deep search
            {
                "number": 8,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Generate final query with comprehensive gap analysis
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Integrate all evidence and generate query for final verification gap.",
                "stage_action": (
                    "Based on all evidence gathered:\n"
                    "1. Summarize key facts from third-hop passages\n"
                    "2. Combine all evidence into comprehensive verification status\n"
                    "3. Identify any remaining gaps\n"
                    "4. Write search query for most critical gap\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What single piece of evidence would most conclusively verify the claim?",
                "example_reasoning": "Example: Third-hop passages discuss imperialism. Summary: Imperialism created colonial tensions. Combined evidence: ... Gaps: How war spread globally. Query: 'how world war i became global war'",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Final retrieval with deep search
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