def entrypoint():
    return {
        "system_prompt": (
            "You are an expert evidence specialist focused on verifying claims through multi-hop retrieval. "
            "Your goal is to maximize retrieval coverage by generating precise search queries and concise evidence summaries. "
            "When asked for a search query, output ONLY the query string with no additional text, explanations, or formatting. "
            "When summarizing evidence, be factual and concise, focusing only on information relevant to the claim."
        ),
        "steps": [
            # Step 1: First-hop retrieval with high recall
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
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify the most important facts that support or refute the claim. "
                    "Write a concise summary of these facts."
                ),
                "reasoning_questions": (
                    "What are the key entities and events mentioned? "
                    "How do they relate to the claim?"
                ),
                "example_reasoning": (
                    "The claim is: 'The telephone was invented by Alexander Graham Bell.'\n"
                    "Retrieved passages:\n"
                    "[1] Bell Telephone Company | Alexander Graham Bell patented the telephone in 1876.\n"
                    "[2] Elisha Gray | Elisha Gray filed a caveat for a telephone device on February 14, 1876.\n"
                    "Summary: Alexander Graham Bell patented the telephone in 1876, but Elisha Gray also filed a caveat for a similar device on the same day."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, determine what additional evidence is needed to fully verify the claim. "
                    "Write a concise search query to find the missing evidence. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is still missing? "
                    "What keywords would find it?"
                ),
                "example_reasoning": "priority date of Bell and Gray telephone patents",
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
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify the most important facts that support or refute the claim. "
                    "Write a concise summary of these facts."
                ),
                "reasoning_questions": (
                    "What new information does this provide? "
                    "How does it fill the gap identified in the previous step?"
                ),
                "example_reasoning": (
                    "The claim is: 'The telephone was invented by Alexander Graham Bell.'\n"
                    "Previous gap: priority date of patents.\n"
                    "Retrieved passages:\n"
                    "[1] Patent Office records | Bell's patent was issued on March 7, 1876, after Gray's caveat was filed but before Gray's patent application.\n"
                    "Summary: Bell's patent was issued on March 7, 1876, after Gray filed a caveat but before Gray submitted a full patent application."
                ),
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence summaries so far, determine what final piece of evidence is needed to fully verify the claim. "
                    "Write a concise search query to find this evidence. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical missing information now? "
                    "What query would best retrieve it?"
                ),
                "example_reasoning": "court ruling on Bell vs Gray patent dispute",
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify the most important facts that support or refute the claim. "
                    "Write a concise summary of these facts."
                ),
                "reasoning_questions": (
                    "Does this evidence resolve the remaining gap? "
                    "What new information is provided?"
                ),
                "example_reasoning": (
                    "The claim is: 'The telephone was invented by Alexander Graham Bell.'\n"
                    "Previous gap: court ruling on patent dispute.\n"
                    "Retrieved passages:\n"
                    "[1] Supreme Court case | The U.S. Supreme Court upheld Bell's patent in 1888, rejecting Gray's claims.\n"
                    "Summary: The U.S. Supreme Court upheld Bell's patent in 1888, confirming his invention."
                ),
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query with gap enumeration
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical remaining evidence gap and generate a search query for the fourth hop.",
                "stage_action": (
                    "Review all evidence summaries (first, second, and third hops). "
                    "Internally list the specific pieces of missing information required to verify the claim. "
                    "Then, write a concise search query to find the most critical missing evidence. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "After three hops, what is the single most important missing fact? "
                    "What query would retrieve it?"
                ),
                "example_reasoning": "earliest known use of the word 'telephone'",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval with high recall
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