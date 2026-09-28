def entrypoint():
    return {
        "system_prompt": "You are an evidence retrieval assistant specialized in multi-hop claim verification. Your role is to analyze claims, extract precise facts from retrieved passages, and generate focused search queries to gather missing evidence. Always prioritize factual accuracy, relevance to the claim, and concise output. For query generation steps, output ONLY the search query string without any additional text.",
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
                "stage_action": "Read the retrieved passages and extract specific entities, dates, numerical values, and key relationships. Omit general background. Format as a structured list of facts.",
                "reasoning_questions": "What specific entities (people, places, organizations) are mentioned? What exact dates or numerical values are provided? What information is still missing to verify the claim?",
                "example_reasoning": "Example 1:\nClaim: 'The Eiffel Tower was completed in 1889.'\nPassages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889. [2] Paris | A major tourist attraction since the late 19th century.\nExtracted facts: ['Eiffel Tower construction completed: 1889']\n\nExample 2:\nClaim: 'Albert Einstein was born in Ulm, Germany.'\nPassages: [1] Albert Einstein | Born in Ulm, Germany on March 14, 1879. [2] Nobel Prize | Awarded in 1921 for his work on the photoelectric effect.\nExtracted facts: ['Albert Einstein birthplace: Ulm, Germany', 'Albert Einstein birth date: March 14, 1879']",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a precise second-hop search query.",
                "stage_action": "Based on the summary, determine what additional evidence is needed to fully verify the claim. Write a concise search query to find the missing evidence. IMPORTANT: Your entire response must be the search query string and nothing else. Do not include any other text, not even a period. Example: 'Marie Curie first Nobel Prize year'",
                "reasoning_questions": "",
                "example_reasoning": "Example 1:\nClaim: 'Marie Curie won her first Nobel Prize in 1903.'\nFirst-hop summary: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\nMissing: year of first Nobel Prize\nMarie Curie first Nobel Prize year\n\nExample 2:\nClaim: 'The first moon landing occurred on July 20, 1969.'\nFirst-hop summary: ['Apollo 11 launched on July 16, 1969.', 'The lunar module landed on the Moon.']\nMissing: exact date of moon landing\nApollo 11 moon landing date\n\nExample 3:\nClaim: 'The Treaty of Versailles was signed in 1919.'\nFirst-hop summary: ['The Treaty of Versailles ended World War I.', 'It was negotiated in Paris.']\nMissing: year of signing\nTreaty of Versailles signing year",
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
                "aim": "Integrate first-hop and second-hop evidence into a comprehensive, structured summary of claim-relevant facts.",
                "stage_action": "Integrate the first-hop summary (which is already a structured list of facts) with the second-hop passages. Extract only new facts from the second-hop passages that are relevant to the claim. Append these new facts to the first-hop summary. Do not re-extract facts from the first-hop summary. Format as a structured list of facts covering all evidence.",
                "reasoning_questions": "What new facts were added by the second-hop passages? What specific entities, dates, or numerical values are now known? What critical information is still missing to verify the claim?",
                "example_reasoning": "Example:\nFirst-hop summary: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\nSecond-hop passages: [1] Nobel Prize | Marie Curie won her first Nobel Prize in Physics in 1903. [2] Radioactivity | She isolated radium and polonium.\nIntegrated facts: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.', 'Marie Curie won her first Nobel Prize in Physics in 1903.', 'She isolated radium and polonium.']",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining critical missing evidence and generate a precise third-hop search query that may cover multiple related gaps using query expansion techniques (last opportunity).",
                "stage_action": "This is the final retrieval step. Identify the critical missing pieces of evidence required to verify the claim. Generate a search query that combines multiple related gaps using OR operators and synonyms to maximize recall. IMPORTANT: Your entire response must be the search query string and nothing else. Do not include any other text. Example: 'apollo 11 landing date OR apollo 11 moonwalk date'",
                "reasoning_questions": "",
                "example_reasoning": "Example 1:\nClaim: 'The first moon landing occurred on July 20, 1969.'\nCurrent evidence: ['Apollo 11 launched on July 16, 1969.', 'The lunar module landed on the Moon.']\nMissing: exact date of moon landing\napollo 11 landing date OR apollo 11 moonwalk date\n\nExample 2:\nClaim: 'The human genome was fully sequenced in 2003.'\nCurrent evidence: ['The Human Genome Project began in 1990.', 'It was an international effort.']\nMissing: completion year\nhuman genome project completion year OR when was human genome sequenced",
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
