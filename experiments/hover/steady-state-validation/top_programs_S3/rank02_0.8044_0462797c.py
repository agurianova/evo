def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop evidence retrieval for claim verification. Your task is to help gather all relevant evidence from Wikipedia abstracts. In steps where you are asked to generate a search query, output ONLY the query string and nothing else.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
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
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (with reasoning scaffolds)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact or piece of information is still missing to verify the claim? Which entities or concepts from the claim and existing evidence should be the focus of the next search?",
                "example_reasoning": "Example:\nClaim: 'The Eiffel Tower was built in 1887.'\nExisting evidence:\n[1] Paris | The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris.\n[2] Gustave Eiffel | Gustave Eiffel was a French civil engineer.\nMissing: The exact year of construction.\nQuery: 'Eiffel Tower construction year'",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (upgraded to deep)
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
            # Step 5: Summarize first and second hop from raw passages
            {
                "number": 5,
                "title": "Summarize first and second hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop raw passages (step1) with the second-hop raw passages (step4). "
                    "Extract all relevant facts and produce a comprehensive evidence summary covering both hops."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],
            },
            # Step 6: Generate third-hop query (with reasoning scaffolds)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact or piece of information is still missing to verify the claim? Which entities or concepts from the claim and existing evidence should be the focus of the next search?",
                "example_reasoning": "Example:\nClaim: 'The Eiffel Tower was built in 1887.'\nExisting evidence:\n[1] Paris | The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris.\n[2] Gustave Eiffel | Gustave Eiffel was a French civil engineer.\n[3] Eiffel Tower construction | Construction of the Eiffel Tower began in 1887.\nMissing: The exact completion year.\nQuery: 'Eiffel Tower completion year'",
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval (deeper search)
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
            # Step 8: Gap analysis after third hop
            {
                "number": 8,
                "title": "Analyze evidence gaps after third hop",
                "step_type": "llm",
                "aim": "Identify missing evidence required to verify the claim based on all retrieved passages from three hops.",
                "stage_action": (
                    "Review all retrieved passages from the first, second, and third hops. "
                    "Determine what specific facts are still missing to fully verify the claim. "
                    "Output a concise description of the gap."
                ),
                "reasoning_questions": "What specific fact or piece of information is still missing? Which entities or concepts from the claim and existing evidence should be the focus of the next search?",
                "example_reasoning": "Example:\nClaim: 'The Great Wall of China is visible from space.'\nExisting evidence:\n[1] Great Wall of China | The Great Wall is a series of fortifications made of stone, brick, tamped earth, wood, and other materials.\n[2] Visibility from space | Astronauts report that the Great Wall is difficult to see from low Earth orbit without magnification.\n[3] Chinese space program | China has sent astronauts to space.\nMissing: Whether the Great Wall is visible to the naked eye from space. The gap is the lack of a definitive statement from astronauts or space agencies about visibility.\nGap description: 'Definitive evidence on whether the Great Wall of China is visible to the naked eye from low Earth orbit.'",
                "dependencies": [1, 4, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a search query to find the missing evidence identified in the gap analysis.",
                "stage_action": (
                    "Based on the gap analysis, write a concise search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? Which entities or concepts from the gap description should be included in the query?",
                "example_reasoning": "Example:\nGap description: 'Definitive evidence on whether the Great Wall of China is visible to the naked eye from low Earth orbit.'\nQuery: 'Great Wall of China visible from space astronauts'",
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval
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
