def entrypoint():
    return {
        "system_prompt": "Expert in multi-hop QA: produce minimal required output at each step.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages.",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop passages
            {
                "number": 2,
                "title": "Summarize key facts from passages.",
                "step_type": "llm",
                "aim": "Extract key facts from the provided passages relevant to the question.",
                "stage_action": (
                    "Extract key facts that are directly relevant to the question OR that establish relationships between entities required for multi-hop reasoning. "
                    "Exclude facts about unrelated entities or background details that do not support the reasoning chain. "
                    "List each fact as a short phrase without conclusions."
                ),
                "reasoning_questions": (
                    "Which facts directly involve the main entities in the question? "
                    "Which facts are necessary to identify missing information for the next hop? "
                    "Exclude facts about unrelated entities or background details."
                ),
                "example_reasoning": (
                    "Question: What is the birth year of the author of 'Pride and Prejudice'?\n"
                    "Passages: [0] Jane Austen | Jane Austen was an English novelist. She wrote 'Pride and Prejudice' in 1813. [1] Pride and Prejudice | This novel was published in 1813.\n"
                    "Reasoning: The question asks for the birth year of the author. The author is Jane Austen (from [0]). The passages do not state her birth year, but they state she wrote the book in 1813. "
                    "This publication year may help infer her birth year (e.g., if we know she was 20 when publishing). "
                    "Relevant facts:\n"
                    "- Jane Austen wrote 'Pride and Prejudice' in 1813.\n"
                    "Excluded: 'Jane Austen was an English novelist' (background, not directly relevant to birth year)."
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query.",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query.",
                "stage_action": (
                    "Determine the specific missing fact needed to answer the question. "
                    "Output ONLY the search query as a string of space-separated terms. Do not use any delimiters or extra text. "
                    "For better retrieval, use multiple relevant terms (e.g., 'Jane Austen birth year biography')."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to answer the question? "
                    "How can we phrase a multi-term query to retrieve exactly that information without being too broad or narrow?"
                ),
                "example_reasoning": (
                    "Question: What is the birth year of the author of 'Pride and Prejudice'?\n"
                    "First-hop summary: Jane Austen wrote 'Pride and Prejudice' in 1813.\n"
                    "Reasoning: The question asks for the birth year of the author. The summary identifies the author as Jane Austen and provides the publication year (1813). "
                    "We need Jane Austen's birth year to answer the question. "
                    "A good query uses multiple terms to capture context.\n"
                    "Jane Austen birth year biography early life"
                ),
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages.",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Combine evidence
            {
                "number": 5,
                "title": "Combine evidence",
                "step_type": "llm",
                "aim": "Integrate evidence from both hops, resolving conflicts using context-aware rules.",
                "stage_action": (
                    "Combine the first-hop summary and second-hop passages into a unified evidence set. "
                    "If there are explicit contradictions (e.g., different numbers or dates for the same fact):\n"
                    "1. If the fact is about a historical origin (e.g., birth, invention, discovery), prefer the earliest date.\n"
                    "2. If the fact is about a current state (e.g., population, status), prefer the most recent date.\n"
                    "3. If no dates are available, prefer the fact from a passage whose title exactly matches a key entity in the question.\n"
                    "4. If none of the above apply, prefer the fact from the second-hop passages because they were generated to fill a specific information gap.\n"
                    "If evidence is consistent, combine facts. Do not invent conflicts."
                ),
                "reasoning_questions": (
                    "What are the key facts from each hop? Are there explicit contradictions? "
                    "If yes, is the fact about a historical origin or current state? Apply the appropriate rule. "
                    "If no contradictions, how do facts complement each other?"
                ),
                "example_reasoning": (
                    "Question: Who invented the telephone?\n"
                    "First-hop summary: Alexander Graham Bell is credited with inventing the telephone in 1876.\n"
                    "Second-hop passages: [0] Antonio Meucci | Meucci demonstrated a voice-communication device in 1860. [1] Telephone | The patent was awarded to Bell in 1876.\n"
                    "Reasoning: First-hop states Bell invented in 1876. Second-hop [0] states Meucci demonstrated in 1860. "
                    "Contradiction: Bell vs Meucci. The fact is about a historical origin (invention), so we prefer the earliest date (1860). "
                    "Unified evidence: Antonio Meucci invented the telephone."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Final answer
            {
                "number": 6,
                "title": "Final answer",
                "step_type": "llm",
                "aim": "Answer the question using all gathered evidence.",
                "stage_action": (
                    "Extract ONLY the minimal direct answer phrase (e.g., 'Paris', '14.0 million') without any extra text, units, or qualifiers. "
                    "Output EXACTLY in format: Answer: <answer>"
                ),
                "reasoning_questions": (
                    "What is the shortest phrase that directly answers the question? "
                    "Have you removed all extra context, units, and qualifiers? "
                    "Verify it is supported by the evidence."
                ),
                "example_reasoning": (
                    "Question: What is the population of Tokyo?\n"
                    "Combined evidence: \n- Tokyo's population was estimated at 14.0 million in 2020.\n"
                    "Reasoning: The minimal direct answer phrase is '14.0 million'. We remove the qualifier 'in 2020' because it is not part of the core answer.\n"
                    "Answer: 14.0 million"
                ),
                "dependencies": [2, 5],
                "frozen": False,
            },
        ],
    }
