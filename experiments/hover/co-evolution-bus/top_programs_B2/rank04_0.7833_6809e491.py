def entrypoint():
    return {
        "system_prompt": "You are an evidence assistant. Extract facts with claim-matching precision. For query steps (3,6): output STRICTLY the query string without any extra text. Ensure the query contains all critical terms for the missing evidence.",
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
                "stage_action": "Break the claim into its essential elements (e.g., entities, actions, time, location, numerical values). Read the claim and retrieved passages. Extract precise, claim-relevant facts for each element: specific entities, dates (with claim-matching precision), numerical values (with units and original precision), and key relationships. For false claims, extract the correct fact without negating the claim. Omit general background. Update facts with more recent/specific evidence and remove duplicates. Format as a structured list of facts.",
                "reasoning_questions": "What specific entities (people, places, organizations) are mentioned? What exact dates or numerical values are provided? What information is still missing to verify the claim?",
                "example_reasoning": "Example 1:\nClaim: 'The Eiffel Tower was completed in 1889.'\nPassages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889. [2] Paris | A major tourist attraction since the late 19th century.\nExtracted facts: ['Eiffel Tower construction completed: 1889']\n\nExample 2:\nClaim: 'Albert Einstein was born in Ulm, Germany.'\nPassages: [1] Albert Einstein | Born in Ulm, Germany on March 14, 1879. [2] Nobel Prize | Awarded in 1921 for his work on the photoelectric effect.\nExtracted facts: ['Albert Einstein birthplace: Ulm, Germany', 'Albert Einstein birth date: 1879-03-14']\n\nExample 3:\nClaim: 'The Battle of Hastings occurred in 1066.'\nPassages: [1] Battle of Hastings | Took place on October 14, 1066. [2] Norman conquest | The battle was fought in 1067 according to some sources.\nExtracted facts: ['Battle of Hastings date: 1066-10-14']\n\nExample 4:\nClaim: 'The Earth is flat.'\nPassages: [1] Earth | The Earth is an oblate spheroid. [2] Geography | Ancient Greeks knew the Earth was round.\nExtracted facts: ['Earth shape: oblate spheroid']",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a precise second-hop search query.",
                "stage_action": "Based on the claim decomposition and summary, identify the most critical missing evidence. Write a concise search query for that gap, including exactly 3 common and relevant aliases for key entities (e.g., 'Marie Curie', 'Maria Sklodowska-Curie', 'Manya Sklodowska'). Avoid redundant terms (e.g., do not include both 'date' and 'when'). Output STRICTLY the query string without any extra text.",
                "reasoning_questions": "What specific claim element lacks supporting evidence? What entity or concept is missing to verify the claim? Prioritize gaps that directly confirm/refute the claim's main assertion.",
                "example_reasoning": "Example 1:\nClaim: 'Marie Curie won her first Nobel Prize in 1903.'\nFirst-hop summary: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\nMarie Curie Maria Sklodowska-Curie Manya Sklodowska first Nobel Prize year\n\nExample 2:\nClaim: 'The first moon landing occurred on July 20, 1969.'\nFirst-hop summary: ['Apollo 11 launched on July 16, 1969.', 'The lunar module landed on the Moon.']\nApollo 11 moon landing date\n\nExample 3:\nClaim: 'The Treaty of Versailles was signed in 1919.'\nFirst-hop summary: ['The Treaty of Versailles ended World War I.', 'It was negotiated in Paris.']\nTreaty of Versailles signing year",
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
                "stage_action": "Break the claim into its essential elements (e.g., entities, actions, time, location, numerical values). Integrate the first-hop summary with the second-hop passages. Extract new facts from the second-hop passages that are relevant to the claim. Update existing facts with more recent/specific evidence and remove duplicates. When conflicting evidence exists, prefer the most recent and official source, but if the claim specifies a time period, prioritize evidence from that period. Do not discard older facts if they are relevant to the claim's context. For numerical values, include units and maintain the original precision. Format as a structured list of facts covering all evidence.",
                "reasoning_questions": "What new facts were added by the second-hop passages? What specific entities, dates, or numerical values are now known? What critical information is still missing to verify the claim?",
                "example_reasoning": "Example 1:\nFirst-hop summary: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\nSecond-hop passages: [1] Nobel Prize | Marie Curie won her first Nobel Prize in Physics in 1903. [2] Radioactivity | She isolated radium and polonium.\nIntegrated facts: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.', 'Marie Curie won her first Nobel Prize in Physics in 1903.', 'She isolated radium and polonium.']\n\nExample 2:\nClaim: 'The speed of light is 299,792,458 meters per second.'\nFirst-hop summary: ['Light is an electromagnetic wave.', 'It travels at a constant speed in vacuum.']\nSecond-hop passages: [1] Speed of light | The exact speed is 299,792,458 meters per second. [2] Physics | This value is defined in the SI system.\nIntegrated facts: ['Light is an electromagnetic wave.', 'It travels at a constant speed in vacuum.', 'Speed of light: 299,792,458 meters per second']\n\nExample 3:\nClaim: 'The population of Tokyo is 13.5 million.'\nFirst-hop summary: ['Tokyo population: 13.5 million (2015 estimate)']\nSecond-hop passages: [1] Tokyo demographics | The population was 13.96 million in 2020. [2] Japan Statistics Bureau | Tokyo metropolitan area population: 37.4 million (2019).\nIntegrated facts: ['Tokyo population: 13.96 million (2020)']",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the single most critical missing piece of evidence and generate a precise third-hop search query including entity aliases.",
                "stage_action": "Based on the claim decomposition and integrated evidence, identify the single most critical missing piece of evidence. Generate a search query that includes the key entities and exactly 4 common and relevant aliases for key entities. Avoid redundant terms (e.g., do not include both 'date' and 'when'). Output STRICTLY the query string without any extra text.",
                "reasoning_questions": "What is the single most critical missing piece of evidence? Prioritize the gap that directly confirms/refutes the claim's main assertion. Express this gap as a concise query with key terms and 4 common aliases for entities, avoiding redundancy.",
                "example_reasoning": "Example 1:\nClaim: 'The first moon landing occurred on July 20, 1969.'\nCurrent evidence: ['Apollo 11 launched on July 16, 1969.', 'The lunar module landed on the Moon.']\nApollo 11 moon landing date\n\nExample 2:\nClaim: 'The human genome was fully sequenced in 2003.'\nCurrent evidence: ['The Human Genome Project began in 1990.', 'It was an international effort.']\nHuman Genome Project completion year\n\nExample 3:\nClaim: 'Marie Curie won her first Nobel Prize in 1903.'\nCurrent evidence: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\nMarie Curie Maria Sklodowska-Curie Manya Sklodowska Maria Salomea Sklodowska-Curie first Nobel Prize year",
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
