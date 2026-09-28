def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Your goal is to gather as much relevant evidence as possible from Wikipedia to verify the claim. Always prioritize completeness of evidence over brevity. When generating search queries, focus on missing information that would help verify the claim.",
        "steps": [
            # Step 1: First-hop retrieval (deep)
            {
                "number": 1,
                "title": "Retrieve first-hop passages (deep)",
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
                "aim": "Extract key facts from the retrieved passages relevant to the claim. Prioritize completeness of evidence.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: For the claim 'The Eiffel Tower was built in 1889', the retrieved passages mention: "
                    "[1] Paris | The Eiffel Tower was completed in 1889. "
                    "[2] Gustave Eiffel | Designed the tower for the 1889 World's Fair. "
                    "Key facts: The Eiffel Tower was built in 1889 and was designed by Gustave Eiffel for the World's Fair."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop. Prioritize completeness of evidence.",
                "stage_action": (
                    "Based on the summary (step2), determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The Eiffel Tower was built in 1889'. "
                    "First-hop summary: The Eiffel Tower was built in 1889 and designed by Gustave Eiffel. "
                    "Missing: Who was the chief engineer? Query: 'Eiffel Tower chief engineer'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep)
            {
                "number": 4,
                "title": "Retrieve second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim. Prioritize completeness of evidence.",
                "stage_action": (
                    "Read all second-hop retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: For the claim 'The Eiffel Tower was built in 1889', second-hop passages: "
                    "[1] Maurice Koechlin | Chief engineer of the Eiffel Tower. "
                    "[2] Émile Nouguier | Co-engineer of the Eiffel Tower. "
                    "Key facts: Maurice Koechlin was the chief engineer and Émile Nouguier was a co-engineer."
                ),
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the third hop. Prioritize completeness of evidence.",
                "stage_action": (
                    "Based on the first-hop evidence summary (step2) and second-hop evidence summary (step5), "
                    "determine what additional evidence is needed to fully verify the claim. "
                    "Write a concise search query to find the missing evidence.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The Eiffel Tower was built in 1889'. "
                    "First-hop: Built in 1889, designed by Gustave Eiffel. "
                    "Second-hop: Chief engineer Maurice Koechlin. "
                    "Missing: Was it the tallest structure at the time? Query: 'Eiffel Tower tallest structure 1889'"
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (deep)
            {
                "number": 7,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim. Prioritize completeness of evidence.",
                "stage_action": (
                    "Read all third-hop retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: For the claim 'The Eiffel Tower was built in 1889', third-hop passages: "
                    "[1] Tallest structure | The Eiffel Tower was the tallest man-made structure until 1930. "
                    "[2] Height | 330 meters tall. "
                    "Key facts: The Eiffel Tower was the tallest structure until 1930 and is 330 meters tall."
                ),
                "dependencies": [7],
            },
            # Step 9: Integrate all evidence and generate fourth-hop query
            {
                "number": 9,
                "title": "Integrate all evidence and generate fourth-hop query",
                "step_type": "llm",
                "aim": "Combine all evidence from first, second, and third hops into a comprehensive summary and identify any remaining gaps to generate a fourth-hop query if needed. Prioritize completeness of evidence.",
                "stage_action": (
                    "Integrate the first-hop evidence summary (step2), second-hop evidence summary (step5), "
                    "and third-hop evidence summary (step8) into a unified evidence summary covering all relevant facts. "
                    "Then, determine if there are still gaps in the evidence that would help verify the claim. "
                    "If gaps exist, write a concise search query to find the missing evidence. "
                    "If no gaps remain, write 'NO_QUERY_NEEDED'. "
                    "\nProvide ONLY the search query or 'NO_QUERY_NEEDED', no additional text."
                ),
                "reasoning_questions": (
                    "What specific facts are still missing to verify the claim? "
                    "\nIs there any part of the claim that remains unverified? "
                    "\nWhat is the most critical missing piece of evidence?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'The Eiffel Tower was built in 1889'. "
                    "Step2: Built in 1889, designed by Gustave Eiffel. "
                    "Step5: Chief engineer Maurice Koechlin. "
                    "Step8: Tallest structure until 1930, 330 meters tall. "
                    "Integrated summary: Built in 1889, designed by Gustave Eiffel, chief engineer Maurice Koechlin, "
                    "was the tallest structure until 1930, and is 330 meters tall. "
                    "Missing: How many workers died during construction? Query: 'Eiffel Tower construction worker deaths'"
                ),
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (deep)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }