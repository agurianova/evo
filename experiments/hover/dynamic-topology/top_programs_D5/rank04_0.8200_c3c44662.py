def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. For each hop, focus exclusively on identifying and retrieving evidence for unverified aspects of the claim. Always refer back to the original claim and the gaps identified in previous evidence. After retrieving evidence for a hop, summarize only the facts relevant to the unverified parts. When generating a query for the next hop, base it solely on the gaps identified in the current evidence. If there are multiple independent gaps, generate separate queries for each gap to cover them in parallel. If evidence for one gap reveals a new unverified aspect, address that new gap next. Focus on factual accuracy and avoid speculation.",
        "steps": [
            # Step 1: First-hop retrieval with standard search (k=7 for precision)
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
            # Step 2: Summarize first-hop evidence and identify up to three gaps
            {
                "number": 2,
                "title": "Summarize first-hop evidence and identify gaps",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop retrieved passages and identify up to three specific unverified aspects (gaps) in the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that directly relate to the main entities and events in the claim. "
                    "Produce a concise summary of the most important evidence found, focusing exclusively on aspects that verify or contradict the claim. "
                    "Then, list up to three specific unverified aspects (gaps) that remain, numbered as '1.', '2.', and '3.' "
                    "If the claim is fully verified, state 'The claim is fully verified.' and list no gaps."
                ),
                "reasoning_questions": (
                    "1. What are the main entities and events mentioned in the claim?\n"
                    "2. Which facts in the passages directly support or contradict the claim?\n"
                    "3. What specific aspects of the claim remain unverified? Identify up to three independent gaps."
                ),
                "example_reasoning": (
                    "Example: Claim: 'Marie Curie was the first woman to win a Nobel Prize, and she was born in 1867 in Warsaw, which was then part of Russia.'\n"
                    "Passages: [1] Title | Marie Curie was born Maria Sklodowska in Warsaw in 1867. [2] Title | She won the Nobel Prize in Physics in 1903.\n"
                    "Summary: Marie Curie was born in Warsaw in 1867 and won the Nobel Prize in Physics in 1903.\n"
                    "Unverified aspects:\n"
                    "1. Was she the first woman to win a Nobel Prize?\n"
                    "2. Was Warsaw part of Russia in 1867?\n"
                    "3. Did she win two Nobel Prizes in different sciences?"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for first gap
            {
                "number": 3,
                "title": "Generate query for first gap",
                "step_type": "llm",
                "aim": "Generate a precise search query for the first unverified aspect (gap) identified in the first-hop evidence summary.",
                "stage_action": (
                    "Based on the first-hop evidence summary, extract the first unverified aspect (gap) listed under '1.' "
                    "If the summary states the claim is fully verified or there is no first gap, output 'NO_GAP'. "
                    "Otherwise, generate a search query to retrieve evidence for ONLY that unverified aspect.\n"
                    "Provide ONLY the search query or 'NO_GAP', no additional text."
                ),
                "reasoning_questions": (
                    "1. What is the first unverified aspect (gap) listed in the summary?\n"
                    "2. What entities or events should the query focus on to address this gap?\n"
                    "3. How can the query be phrased to retrieve the most relevant evidence without being too broad?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'Marie Curie was the first woman to win a Nobel Prize.'\n"
                    "Summary: Marie Curie won the Nobel Prize in Physics in 1903 and Chemistry in 1911.\n"
                    "Unverified aspects:\n"
                    "1. Was she the first woman to win a Nobel Prize?\n"
                    "'first woman Nobel Prize winner before Marie Curie'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval for first gap
            {
                "number": 4,
                "title": "Retrieve passages for first gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Generate query for second gap
            {
                "number": 5,
                "title": "Generate query for second gap",
                "step_type": "llm",
                "aim": "Generate a precise search query for the second unverified aspect (gap) if it exists.",
                "stage_action": (
                    "Based on the first-hop evidence summary, extract the second unverified aspect (gap) listed under '2.' "
                    "If there is no second gap listed, output 'NO_GAP'. "
                    "Otherwise, generate a search query to retrieve evidence for ONLY that unverified aspect.\n"
                    "Provide ONLY the search query or 'NO_GAP', no additional text."
                ),
                "reasoning_questions": (
                    "1. What is the second unverified aspect (gap) listed in the summary?\n"
                    "2. What entities or events should the query focus on to address this gap?\n"
                    "3. How can the query be phrased to retrieve the most relevant evidence without being too broad?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'Marie Curie was born in Warsaw, which was then part of Russia.'\n"
                    "Summary: Marie Curie was born in Warsaw in 1867.\n"
                    "Unverified aspects:\n"
                    "1. Was the year of birth 1867?\n"
                    "2. Was Warsaw part of Russia in 1867?\n"
                    "'Warsaw part of Russia 1867'"
                ),
                "dependencies": [2],
            },
            # Step 6: Second-hop retrieval for second gap
            {
                "number": 6,
                "title": "Retrieve passages for second gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [5],
            },
            # Step 7: Generate query for third gap
            {
                "number": 7,
                "title": "Generate query for third gap",
                "step_type": "llm",
                "aim": "Generate a precise search query for the third unverified aspect (gap) if it exists.",
                "stage_action": (
                    "Based on the first-hop evidence summary, extract the third unverified aspect (gap) listed under '3.' "
                    "If there is no third gap listed, output 'NO_GAP'. "
                    "Otherwise, generate a search query to retrieve evidence for ONLY that unverified aspect.\n"
                    "Provide ONLY the search query or 'NO_GAP', no additional text."
                ),
                "reasoning_questions": (
                    "1. What is the third unverified aspect (gap) listed in the summary?\n"
                    "2. What entities or events should the query focus on to address this gap?\n"
                    "3. How can the query be phrased to retrieve the most relevant evidence without being too broad?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'Marie Curie won two Nobel Prizes in different sciences.'\n"
                    "Summary: Marie Curie won the Nobel Prize in Physics in 1903 and Chemistry in 1911.\n"
                    "Unverified aspects:\n"
                    "3. Did she win two Nobel Prizes in different sciences?\n"
                    "'Marie Curie Nobel Prizes different sciences'"
                ),
                "dependencies": [2],
            },
            # Step 8: Second-hop retrieval for third gap
            {
                "number": 8,
                "title": "Retrieve passages for third gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Analyze second-hop evidence and generate query for third hop
            {
                "number": 9,
                "title": "Analyze second-hop evidence and generate query for third hop",
                "step_type": "llm",
                "aim": "Determine if the claim is fully verified after second-hop evidence. If not, generate a search query for the most critical remaining unverified aspect.",
                "stage_action": (
                    "Read the retrieved passages from the second-hop retrievals (steps 4, 6, and 8). "
                    "Summarize the evidence found for each gap. Then, check if the entire claim is now verified. "
                    "If the claim is fully verified, output 'NO_GAP'. "
                    "Otherwise, identify the single most important remaining unverified aspect and generate a search query to retrieve evidence for it. "
                    "Output ONLY the search query or 'NO_GAP', no additional text."
                ),
                "reasoning_questions": (
                    "1. What evidence was found for gap1 (from step 4)?\n"
                    "2. What evidence was found for gap2 (from step 6)?\n"
                    "3. What evidence was found for gap3 (from step 8)?\n"
                    "4. Is there any part of the claim still unverified? If so, what is the most critical unverified aspect?\n"
                    "5. How can a query be phrased to retrieve evidence for that aspect?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'Marie Curie was the first woman to win a Nobel Prize, born in Warsaw in 1867, and won two Nobel Prizes in different sciences.'\n"
                    "Step 4 (gap1: 'first woman Nobel Prize'): [passages showing she was not the first]\n"
                    "Step 6 (gap2: 'Warsaw part of Russia in 1867'): [passages confirming]\n"
                    "Step 8 (gap3: 'won two Nobel Prizes in different sciences'): [passages confirming Physics and Chemistry]\n"
                    "Summary: Gap1: not first (evidence found); Gap2: confirmed; Gap3: confirmed. The claim is fully verified.\n"
                    "Output: NO_GAP\n\n"
                    "Another example: Claim: 'The Eiffel Tower was built in 1889 and is 300 meters tall.'\n"
                    "Step 4 (gap1: 'built in 1889'): [passages confirming 1889]\n"
                    "Step 6 (gap2: '300 meters tall'): [passages saying 300 meters without flagpole, but 330 with]\n"
                    "Step 8 (gap3: none, so step8 returned nothing)\n"
                    "Summary: Gap1: confirmed; Gap2: partially confirmed (300m without flagpole, but total height is 330m); Gap3: none.\n"
                    "Unverified: The claim states '300 meters tall' but evidence shows total height is 330m.\n"
                    "Query: 'Eiffel Tower official height without antenna'"
                ),
                "dependencies": [4, 6, 8],
            },
            # Step 10: Third-hop retrieval
            {
                "number": 10,
                "title": "Retrieve passages for third hop",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }
