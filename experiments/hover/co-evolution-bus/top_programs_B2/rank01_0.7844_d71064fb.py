def entrypoint():
    return {
        "system_prompt": "You are an evidence retrieval assistant specialized in multi-hop claim verification. Your role is to analyze claims, extract precise facts from retrieved passages, and generate focused search queries to gather missing evidence. Always prioritize factual accuracy, relevance to the claim, and concise output. For query generation steps (steps 3 and 6), output EXACTLY and ONLY the search query string with no additional text, explanations, or punctuation. Any extra text will cause system errors. For fact extraction steps, format facts as a structured list of specific entities, dates, numerical values, and key relationships.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
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
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract precise, claim-relevant facts from the first-hop passages to support verification.",
                "stage_action": "Read the retrieved passages and extract specific entities, dates, numerical values, and key relationships. Omit general background. Format as a structured list of facts. If no relevant evidence is found, output 'NO_EVIDENCE' to indicate that the next query should be broadened.",
                "reasoning_questions": "What specific entities (people, places, organizations) are mentioned? What exact dates or numerical values are provided? What information is still missing to verify the claim?",
                "example_reasoning": "Example 1:\nClaim: 'The first moon landing occurred on July 20, 1969.'\nRetrieved passages: [0] Apollo 11 | Apollo 11 was the spaceflight that landed the first two humans on the Moon. Commander Neil Armstrong and lunar module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on July 20, 1969.\nFact extraction:\n  - Mission: Apollo 11\n  - Astronauts: Neil Armstrong, Buzz Aldrin\n  - Lunar module: Eagle\n  - Moon landing date: July 20, 1969\n\nExample 2:\nClaim: 'Marie Curie won her first Nobel Prize in 1903.'\nRetrieved passages: [0] Marie Curie | She shared the 1903 Nobel Prize in Physics with her husband Pierre Curie and Henri Becquerel.\nFact extraction:\n  - First Nobel Prize year: 1903\n  - Co-winners: Pierre Curie, Henri Becquerel\n  - Prize category: Physics\n\nExample 3 (complex):\nClaim: 'The Eiffel Tower was completed in 1889 and is 300 meters tall.'\nRetrieved passages: [0] Eiffel Tower | The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. [1] Gustave Eiffel | Gustave Eiffel was a French civil engineer who designed the Eiffel Tower.\nFact extraction:\n  - Location: Paris, France\n  - Designer: Gustave Eiffel\n  - Structure type: wrought-iron lattice tower\nMissing: completion year and height",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a precise second-hop search query.",
                "stage_action": "Based on the summary, determine what additional evidence is needed to fully verify the claim. Generate a concise, keyword-based search query optimized for Wikipedia BM25 retrieval. Use OR operators to cover multiple related gaps (e.g., 'term1 OR term2 OR term3'). Output ONLY the search query string with no additional text, explanations, or punctuation.",
                "reasoning_questions": "",
                "example_reasoning": "Example 1:\nClaim: 'The first moon landing occurred on July 20, 1969.'\nFirst-hop summary:\n  - Mission: Apollo 11\n  - Astronauts: Neil Armstrong, Buzz Aldrin\nMissing: exact date of moon landing\nApollo 11 moon landing date OR Apollo 11 landing date\n\nExample 2:\nClaim: 'Marie Curie won her first Nobel Prize in 1903.'\nFirst-hop summary:\n  - Marie Curie was a physicist.\n  - She conducted pioneering research on radioactivity.\nMissing: year of first Nobel Prize\nMarie Curie first Nobel Prize year OR Marie Curie Nobel Prize 1903\n\nExample 3 (multi-gap):\nClaim: 'The speed of light is 299,792,458 meters per second and was first measured by Ole Rømer in 1676.'\nFirst-hop summary:\n  - Light travels at a finite speed.\n  - The speed is constant in vacuum.\nMissing: numerical value and first measurement date\nspeed of light value OR speed of light meters per second OR speed of light first measurement year",
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
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
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Integrate first-hop and second-hop evidence into a comprehensive, structured summary of claim-relevant facts, flagging any contradictions.",
                "stage_action": "Preserve the first-hop summary exactly. Then, from the second-hop passages, extract only new facts (specific entities, dates, numerical values, and key relationships) that are relevant to the claim and not already in the first-hop summary. If a new fact contradicts the first-hop summary or the claim, note: 'CONTRADICTION: [fact] vs [existing fact]'. Format as a combined structured list: [first-hop summary] followed by [new second-hop facts] with contradictions flagged.",
                "reasoning_questions": "What new facts were added by the second-hop passages? Are there any contradictions with the first-hop summary or the claim? What specific entities, dates, or numerical values are now known? What critical information is still missing to verify the claim?",
                "example_reasoning": "Example 1:\nFirst-hop summary:\n  - Mission: Apollo 11\n  - Astronauts: Neil Armstrong, Buzz Aldrin\nSecond-hop passages: [0] Moon landing | The Apollo 11 lunar module Eagle landed on the Moon on July 20, 1969, at 20:17 UTC.\nNew facts extracted:\n  - Moon landing date: July 20, 1969\n  - Exact time: 20:17 UTC\nCombined summary:\n  - Mission: Apollo 11\n  - Astronauts: Neil Armstrong, Buzz Aldrin\n  - Moon landing date: July 20, 1969\n  - Exact time: 20:17 UTC\n\nExample 2:\nFirst-hop summary:\n  - Marie Curie was a physicist.\n  - She conducted pioneering research on radioactivity.\nSecond-hop passages: [0] Nobel Prize in Physics 1903 | Marie Curie, Pierre Curie, and Henri Becquerel were awarded the Nobel Prize in Physics in 1903.\nNew facts extracted:\n  - First Nobel Prize year: 1903\n  - Co-winners: Pierre Curie, Henri Becquerel\n  - Prize category: Physics\nCombined summary:\n  - Marie Curie was a physicist.\n  - She conducted pioneering research on radioactivity.\n  - First Nobel Prize year: 1903\n  - Co-winners: Pierre Curie, Henri Becquerel\n  - Prize category: Physics\n\nExample 3 (contradiction):\nClaim: 'The Battle of Hastings occurred in 1066.'\nFirst-hop summary:\n  - Battle of Hastings year: 1066\nSecond-hop passages: [0] Battle of Hastings | Some historians argue the battle took place in 1067.\nNew facts extracted:\n  - CONTRADICTION: Battle of Hastings year: 1067 (from second-hop) vs 1066 (from first-hop and claim)\nCombined summary:\n  - Battle of Hastings year: 1066\n  - CONTRADICTION: Battle of Hastings year: 1067 (from second-hop) vs 1066",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify critical missing evidence and generate a precise third-hop search query that covers multiple related gaps (using OR operators for synonyms/variants) to maximize evidence retrieval in the final hop.",
                "stage_action": "This is the final retrieval step. Identify the critical missing pieces of evidence required to verify the claim. Generate a keyword-based search query optimized for Wikipedia BM25 retrieval, using 2-4 OR operators to cover related terms and gaps (e.g., 'term1 OR term2 OR term3'). Output ONLY the search query string with no additional text, explanations, or punctuation.",
                "reasoning_questions": "",
                "example_reasoning": "Example 1:\nClaim: 'The population of Tokyo in 2020 was 13.96 million.'\nCurrent evidence:\n  - Tokyo is the capital of Japan.\n  - It is a major economic center.\nMissing: population figure for 2020\nTokyo population 2020 OR Tokyo population year 2020 OR Tokyo demographic data 2020\n\nExample 2:\nClaim: 'The speed of light is 299,792,458 meters per second.'\nCurrent evidence:\n  - Light speed is constant in vacuum.\n  - It is denoted by 'c'.\nMissing: exact numerical value and unit\nspeed of light value OR speed of light meters per second OR speed of light exact figure\n\nExample 3:\nClaim: 'The Amazon rainforest produces 20% of the world's oxygen.'\nCurrent evidence:\n  - The Amazon is a large tropical rainforest.\n  - It spans several South American countries.\nMissing: oxygen production percentage\nAmazon rainforest oxygen production OR Amazon oxygen generation percentage OR Amazon oxygen contribution",
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
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
