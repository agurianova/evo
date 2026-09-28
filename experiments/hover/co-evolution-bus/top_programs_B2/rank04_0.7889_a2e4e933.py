def entrypoint():
    return {
        "system_prompt": "You are an evidence assistant. Extract facts with claim-matching precision. For query steps (3,6): output ONLY the query string.",
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
                "aim": "Extract precise, claim-relevant facts from the first-hop passages to support verification, preserving temporal context.",
                "stage_action": "Decompose the claim into subject, predicate, and object. Read the claim and retrieved passages. Extract precise, claim-relevant facts for each component: specific entities, dates (with claim-matching precision), numerical values (with units and original precision), and key relationships. Omit general background. Update facts with more recent/specific evidence ONLY if the claim implies current/present context; otherwise preserve temporal context matching the claim. Remove duplicates. Format as a structured list of facts.",
                "reasoning_questions": "What specific entities (people, places, organizations) are mentioned? What exact dates or numerical values are provided? What information is still missing to verify the claim? Does the claim reference a specific time period that should guide evidence selection?",
                "example_reasoning": "Example 1:\
Claim: 'The Eiffel Tower was completed in 1889.'\
Passages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889. [2] Paris | A major tourist attraction since the late 19th century.\
Extracted facts: ['Eiffel Tower construction completed: 1889']\
\
Example 2:\
Claim: 'Albert Einstein was born in Ulm, Germany.'\
Passages: [1] Albert Einstein | Born in Ulm, Germany on March 14, 1879. [2] Nobel Prize | Awarded in 1921 for his work on the photoelectric effect.\
Extracted facts: ['Albert Einstein birthplace: Ulm, Germany', 'Albert Einstein birth date: 1879-03-14']\
\
Example 3:\
Claim: 'The Battle of Hastings occurred in 1066.'\
Passages: [1] Battle of Hastings | Took place on October 14, 1066. [2] Norman conquest | The battle was fought in 1067 according to some sources.\
Extracted facts: ['Battle of Hastings date: 1066-10-14']\
\
Example 4 (negation):\
Claim: 'Thomas Edison did not invent the telephone.'\
Passages: [1] Alexander Graham Bell | Credited with inventing the telephone in 1876. [2] Thomas Edison | Made significant improvements to telephone technology but did not invent it.\
Extracted facts: ['Telephone inventor: Alexander Graham Bell', 'Thomas Edison improved but did not invent telephone']",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a precise second-hop search query.",
                "stage_action": "Based on the claim decomposition and summary, identify the most critical missing evidence. Write a concise search query for that gap, including 2-3 common aliases for key entities (e.g., 'Marie Curie Sklodowska', 'Maria Sklodowska-Curie'). CRITICAL: Output ONLY the query string with no additional text, formatting, or explanations.",
                "reasoning_questions": "What specific claim element lacks supporting evidence? What entity or concept is missing to verify the claim? Prioritize gaps that directly confirm/refute the claim's main assertion.",
                "example_reasoning": "Example 1:\
Claim: 'Marie Curie won her first Nobel Prize in 1903.'\
First-hop summary: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\
Marie Curie Sklodowska Maria Sklodowska-Curie first Nobel Prize year\
\
Example 2:\
Claim: 'The first moon landing occurred on July 20, 1969.'\
First-hop summary: ['Apollo 11 launched on July 16, 1969.', 'The lunar module landed on the Moon.']\
Apollo 11 moon landing date when\
\
Example 3:\
Claim: 'The Treaty of Versailles was signed in 1919.'\
First-hop summary: ['The Treaty of Versailles ended World War I.', 'It was negotiated in Paris.']\
Treaty of Versailles signing year date\
\
Example 4 (negation):\
Claim: 'Thomas Edison did not invent the telephone.'\
First-hop summary: ['Thomas Edison improved but did not invent telephone']\
Alexander Graham Bell telephone inventor who",
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
                "aim": "Integrate first-hop and second-hop evidence into a comprehensive, structured summary of claim-relevant facts while preserving temporal context.",
                "stage_action": "Decompose the claim into subject, predicate, and object. Integrate the first-hop summary with the second-hop passages. Identify new facts by comparing the first-hop summary and second-hop passages to avoid missing evidence. Extract new facts from the second-hop passages that are relevant to the claim. Update existing facts with more recent/specific evidence ONLY if the claim implies current/present context; otherwise preserve temporal context matching the claim. Remove duplicates. For numerical values, include units and maintain the original precision. Format as a structured list of facts covering all evidence.",
                "reasoning_questions": "What new facts were added by the second-hop passages? What specific entities, dates, or numerical values are now known? What critical information is still missing to verify the claim? Does the claim reference a specific time period that should guide evidence selection?",
                "example_reasoning": "Example 1:\
First-hop summary: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\
Second-hop passages: [1] Nobel Prize | Marie Curie won her first Nobel Prize in Physics in 1903. [2] Radioactivity | She isolated radium and polonium.\
Integrated facts: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.', 'Marie Curie won her first Nobel Prize in Physics in 1903.', 'She isolated radium and polonium.']\
\
Example 2:\
Claim: 'The speed of light is 299,792,458 meters per second.'\
First-hop summary: ['Light is an electromagnetic wave.', 'It travels at a constant speed in vacuum.']\
Second-hop passages: [1] Speed of light | The exact speed is 299,792,458 meters per second. [2] Physics | This value is defined in the SI system.\
Integrated facts: ['Light is an electromagnetic wave.', 'It travels at a constant speed in vacuum.', 'Speed of light: 299,792,458 meters per second']\
\
Example 3:\
Claim: 'The population of Tokyo is 13.5 million.'\
First-hop summary: ['Tokyo population: 13.5 million (2015 estimate)']\
Second-hop passages: [1] Tokyo demographics | The population was 13.96 million in 2020. [2] Japan Statistics Bureau | Tokyo metropolitan area population: 37.4 million (2019).\
Integrated facts: ['Tokyo population: 13.96 million (2020)']",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify up to two most critical missing pieces of evidence and generate a precise third-hop search query including entity aliases.",
                "stage_action": "Based on the claim decomposition and integrated evidence, identify up to two most critical missing pieces of evidence. Generate a single concise search query that includes key entities, 3-4 common aliases, and alternative phrasings for the missing information (e.g., 'year', 'date', 'when'). CRITICAL: Output ONLY the query string with no additional text, formatting, or explanations.",
                "reasoning_questions": "What are the 1-2 most critical missing pieces of evidence? Prioritize gaps that directly confirm/refute the claim's main assertion. How can you express these gaps as a single effective query including entity aliases and alternative phrasings?",
                "example_reasoning": "Example 1:\
Claim: 'The first moon landing occurred on July 20, 1969.'\
Current evidence: ['Apollo 11 launched on July 16, 1969.', 'The lunar module landed on the Moon.']\
Apollo 11 moon landing date July 20 1969 when did occur\
\
Example 2:\
Claim: 'The human genome was fully sequenced in 2003.'\
Current evidence: ['The Human Genome Project began in 1990.', 'It was an international effort.']\
Human Genome Project completion year 2003 finalized finished when\
\
Example 3:\
Claim: 'Marie Curie won her first Nobel Prize in 1903.'\
Current evidence: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\
Marie Curie Sklodowska Maria Sklodowska-Curie first Nobel Prize year 1903 awarded when\
\
Example 4 (two gaps):\
Claim: 'The Magna Carta was signed by King John in 1215 at Runnymede.'\
Current evidence: ['Magna Carta limited the power of the English monarchy.', 'It was a charter of rights.']\
Magna Carta King John signing year 1215 Runnymede location where\
\
Example 5 (negation):\
Claim: 'Marie Curie did not win a Nobel Prize in Chemistry in 1911.'\
Current evidence: ['Marie Curie won her first Nobel Prize in Physics in 1903']\
Marie Curie Sklodowska Maria Sklodowska-Curie Nobel Prize Chemistry 1911",
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
