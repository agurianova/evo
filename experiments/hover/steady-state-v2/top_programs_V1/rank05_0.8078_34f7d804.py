def entrypoint():
    return {
        "system_prompt": "You are an expert evidence specialist for claim verification. Your goal is to maximize retrieval coverage by systematically identifying and filling evidence gaps. For query generation steps, output ONLY the search query with no additional text.",
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
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": "Read all retrieved passages and identify facts that are relevant to verifying the claim. Summarize the most important evidence found.",
                "reasoning_questions": "What are the main entities and events mentioned? How do these relate to the claim?",
                "example_reasoning": "Passages:\n[1] Paris | Paris is the capital of France.\n[2] France | France is a country in Europe.\n\nSummary: The capital of France is Paris.",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": "Based on the summary, determine what additional evidence is needed to fully verify the claim. Write a concise search query to find the missing evidence. Provide ONLY the search query, no additional text.",
                "reasoning_questions": "What key fact is still missing? What specific information would help verify the claim?",
                "example_reasoning": "Claim: Paris is the capital of France.\nSummary: The capital of France is Paris.\nQuery: when was Paris declared the capital of France",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence (NEW)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": "Read all retrieved passages from the second hop and identify facts that are relevant to verifying the claim. Summarize the most important evidence found.",
                "reasoning_questions": "What new information is provided? How does it relate to the claim and the first-hop evidence?",
                "example_reasoning": "Passages:\n[1] History of Paris | Paris became the capital of France in the 10th century.\n\nSummary: Paris was declared the capital of France in the 10th century.",
                "dependencies": [4],
            },
            # Step 6: Combine evidence and enumerate gaps (REVISED)
            {
                "number": 6,
                "title": "Combine evidence and enumerate gaps",
                "step_type": "llm",
                "aim": "Integrate all evidence gathered so far and explicitly list remaining gaps for verification.",
                "stage_action": "Combine the first-hop evidence summary and the second-hop evidence summary. Then, list all remaining gaps that prevent full verification of the claim. Be specific about what information is missing.",
                "reasoning_questions": "What do we know so far? What specific pieces of information (e.g., dates, sources, numerical values, or event details) are still required to confirm or refute the claim? Are there multiple gaps that need to be addressed?",
                "example_reasoning": "First-hop summary: The Eiffel Tower was built in 1889 for the World's Fair.\nSecond-hop summary: Construction began in 1887 and took 2 years, employing 300 workers.\n\nGaps:\n- What was the exact date of completion?\n- How tall is the tower in meters? (current height including antennas)\n- What materials were used in construction beyond iron?\n- Were there any major engineering challenges during construction?",
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate a search query to address the highest priority remaining gap.",
                "stage_action": "Based on the enumerated gaps, select the most critical gap and write a concise search query to find evidence for it. Provide ONLY the search query, no additional text.",
                "reasoning_questions": "Which gap is most crucial for verification? What specific search terms will yield the most relevant results?",
                "example_reasoning": "Gaps:\n- When exactly in the 10th century?\n- Is there an official document confirming this?\n\nQuery: official declaration of Paris as capital of France date",
                "dependencies": [6],
            },
            # Step 8: Third-hop retrieval (deep)
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
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a search query to address any remaining gaps after the third hop.",
                "stage_action": "First, summarize the evidence from the third-hop retrieval. Then, review the evidence and the previous gap list. If there are still gaps, generate a query for the highest priority remaining gap. If no gaps remain, output 'no_query_needed'. Provide ONLY the search query or 'no_query_needed', no additional text.",
                "reasoning_questions": "Are there still unresolved gaps? If so, what is the next most critical piece of information needed?",
                "example_reasoning": "Example 1 (gaps remain):\nThird-hop evidence: The Eiffel Tower's height is 330 meters including antennas.\nGaps:\n- What was the original height without antennas?\n- When were the antennas added?\n\nQuery: original height of Eiffel Tower without antennas\n\nExample 2 (no gaps):\nThird-hop evidence: Construction of the Eiffel Tower was completed on March 15, 1889.\nGaps: None.\n\nQuery: no_query_needed",
                "dependencies": [6, 8],
            },
            # Step 10: Fourth-hop retrieval (deep)
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