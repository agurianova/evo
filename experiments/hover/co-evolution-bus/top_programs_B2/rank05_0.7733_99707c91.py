def entrypoint():
    return {
        "system_prompt": "You are an evidence retrieval assistant. Extract precise facts and generate bare search queries. For query steps, output ONLY the query string.",
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
                "stage_action": "Read the claim and retrieved passages. Extract specific entities, dates (if the claim states a year, output only the year in YYYY format; otherwise, output the most specific date), numerical values with units and original precision (e.g., '299,792,458 meters per second'), and key relationships. Omit general background. Format as a structured list of facts.",
                "reasoning_questions": "What specific entities (people, places, organizations) are mentioned? What exact dates or numerical values are provided? What information is still missing to verify the claim?",
                "example_reasoning": "Example 1:\nClaim: 'The Eiffel Tower was completed in 1889.'\nPassages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889. [2] Paris | A major tourist attraction since the late 19th century.\nExtracted facts: ['Eiffel Tower construction completed: 1889']\n\nExample 2:\nClaim: 'Albert Einstein was born in Ulm, Germany.'\nPassages: [1] Albert Einstein | Born in Ulm, Germany on March 14, 1879. [2] Nobel Prize | Awarded in 1921 for his work on the photoelectric effect.\nExtracted facts: ['Albert Einstein birthplace: Ulm, Germany', 'Albert Einstein birth date: 1879']",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a precise second-hop search query.",
                "stage_action": "Based on the summary, determine what additional evidence is needed to fully verify the claim. Write a concise search query to find the missing evidence. IMPORTANT: Your entire response must be the search query string and nothing else. WARNING: Any additional text will cause system failure. Example: 'Marie Curie first Nobel Prize year'",
                "reasoning_questions": "What specific claim element lacks supporting evidence? What entity or concept is missing to verify the claim?",
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
                "stage_action": "Integrate the first-hop summary (which is already a structured list of facts) with the second-hop passages. Extract only new facts from the second-hop passages that are relevant to the claim. If new evidence contradicts prior facts, prioritize the source with the most specific date or the one that is an official document (e.g., government publication). Append these new facts to the first-hop summary. Do not re-extract facts from the first-hop summary. Format as a structured list of facts covering all evidence.",
                "reasoning_questions": "What new facts were added by the second-hop passages? What specific entities, dates, or numerical values are now known? What critical information is still missing to verify the claim?",
                "example_reasoning": "Example 1:\nFirst-hop summary: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\nSecond-hop passages: [1] Nobel Prize | Marie Curie won her first Nobel Prize in Physics in 1903. [2] Radioactivity | She isolated radium and polonium.\nIntegrated facts: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.', 'Marie Curie won her first Nobel Prize in Physics in 1903.', 'She isolated radium and polonium.']\n\nExample 2:\nClaim: 'The speed of light is 299,792,458 meters per second.'\nFirst-hop summary: ['Light is an electromagnetic wave.', 'It travels at a constant speed in vacuum.']\nSecond-hop passages: [1] Speed of light | The exact speed is 299,792,458 meters per second. [2] Physics | This value is defined in the SI system.\nIntegrated facts: ['Light is an electromagnetic wave.', 'It travels at a constant speed in vacuum.', 'Speed of light: 299,792,458 meters per second']",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the top 3-4 critical missing evidence gaps and generate a precise third-hop search query using OR expansion to maximize recall.",
                "stage_action": "Identify the 3-4 most critical missing pieces of evidence required to verify the claim. Generate a search query that combines these gaps using OR operators. IMPORTANT: Your entire response must be the search query string and nothing else. WARNING: Any additional text will cause system failure. Example: 'Apollo 11 landing date OR moonwalk time OR astronaut names'",
                "reasoning_questions": "What are the top 3 missing pieces of evidence that would most directly verify the claim? Rank them by verification importance (e.g., direct confirmation of claim's main assertion > supplementary details).",
                "example_reasoning": "Example 1:\nClaim: 'The first moon landing occurred on July 20, 1969.'\nCurrent evidence: ['Apollo 11 launched on July 16, 1969.', 'The lunar module landed on the Moon.']\nMissing: exact date of moon landing, time of moonwalk, names of astronauts\napollo 11 landing date OR apollo 11 moonwalk time OR apollo 11 astronauts\n\nExample 2:\nClaim: 'The human genome was fully sequenced in 2003.'\nCurrent evidence: ['The Human Genome Project began in 1990.', 'It was an international effort.']\nMissing: completion year, lead institutions, sequencing method\nhuman genome project completion year OR human genome project lead institutions OR human genome sequencing method\n\nExample 3:\nClaim: 'The Magna Carta was signed in 1215 by King John of England.'\nCurrent evidence: ['The Magna Carta was a charter agreed by King John.', 'It was sealed at Runnymede.']\nMissing: year of signing, the king's full title, location details\nMagna Carta signing year OR King John full title OR Runnymede location",
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
