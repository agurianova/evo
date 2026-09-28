def entrypoint():
    return {
        "system_prompt": (
            "You are a meticulous fact-checker verifying claims using multi-hop evidence retrieval. "
            "Your goal is to retrieve all relevant evidence to verify the claim by performing necessary retrieval hops. "
            "When generating a search query (in query generation steps), output ONLY the query string with no additional text. "
            "In evidence integration steps, you will be given retrieved passages from previous hops. "
            "Your task is to determine if the evidence is sufficient: if yes, output exactly an empty string ''; "
            "if not, output ONLY the next search query. "
            "Do not output any other text in query generation or integration steps."
        ),
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
            # Step 2: Generate second-hop query from raw first-hop passages
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information from first-hop evidence and generate a search query for the second hop.",
                "stage_action": (
                    "Read the first-hop retrieved passages. Determine what specific information is missing "
                    "to fully verify the claim. Write a concise search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What is the main subject of the claim?\n"
                    "2. Which facts in the retrieved passages directly relate to the claim?\n"
                    "3. What specific detail is still missing to confirm or refute the claim?"
                ),
                "example_reasoning": (
                    "CASE 1: Evidence insufficient after first hop\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Retrieved passages:\n"
                    "  [1] Eiffel Tower | Construction began in January 1887 and was completed in March 1889.\n"
                    "  [2] Gustave Eiffel | Signed the construction contract in 1887.\n"
                    "Analysis: The passages confirm contract signing in 1887 but don't specify when physical construction started.\n"
                    "'Eiffel Tower actual construction start date'\n\n"
                    "CASE 2: Evidence sufficient after first hop (rare)\n"
                    "Claim: 'Paris is the capital of France.'\n"
                    "Retrieved passages:\n"
                    "  [1] France | Paris is the capital and largest city.\n"
                    "  [2] European capitals | Paris serves as the capital of France.\n"
                    "Analysis: Both passages explicitly state that Paris is the capital of France, confirming the claim.\n"
                    "''"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Integrate first two hops and decide if third hop needed
            {
                "number": 4,
                "title": "Integrate evidence from first two hops",
                "step_type": "llm",
                "aim": "Combine evidence from first two hops and determine if additional evidence is required.",
                "stage_action": (
                    "Read all retrieved passages from the first two hops. Then, answer:\n"
                    "- What facts have been established so far?\n"
                    "- What specific information is still missing to verify the claim?\n"
                    "If there are missing facts, write a concise search query to find the missing evidence.\n"
                    "If the evidence is sufficient, output exactly: ''\n"
                    "Do not output any other text."
                ),
                "reasoning_questions": (
                    "1. What key facts are established by the combined evidence from the first two hops?\n"
                    "2. Are there any contradictions between the first-hop and second-hop passages? If so, what is the nature of the conflict?\n"
                    "3. What specific missing detail would resolve the current uncertainty or contradiction?"
                ),
                "example_reasoning": (
                    "CASE 1: Evidence insufficient after two hops\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop passages:\n"
                    "  [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  [2] Paris landmarks | The tower construction started in 1889.\n"
                    "Second-hop passages:\n"
                    "  [1] Gustave Eiffel | Signed contract in 1887 and began site preparation.\n"
                    "  [2] Construction timeline | Foundation work started 1887, tower assembly began 1888.\n"
                    "Analysis:\n"
                    "  Established: Contract signed and foundation work started in 1887.\n"
                    "  Contradiction: 'Construction began' claims vary between 1887-1889.\n"
                    "  Missing: Official start date of tower structure assembly.\n"
                    "'Eiffel Tower tower structure assembly start date'\n\n"
                    "CASE 2: Evidence sufficient after two hops\n"
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "First-hop passages:\n"
                    "  [1] Apollo 11 | Launched on July 16, 1969, and landed on the moon on July 20, 1969.\n"
                    "  [2] Space exploration | The first manned moon landing was in 1969.\n"
                    "Second-hop passages:\n"
                    "  [1] NASA archives | Apollo 11 mission successfully landed astronauts on the moon in July 1969.\n"
                    "  [2] Historical records | The moon landing took place on July 20, 1969.\n"
                    "Analysis:\n"
                    "  Established: Multiple sources confirm the moon landing occurred in July 1969.\n"
                    "  No contradictions or missing details that affect the year.\n"
                    "  The claim is fully verified.\n"
                    "''"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Integrate first three hops and decide if fourth hop needed
            {
                "number": 6,
                "title": "Integrate evidence from first three hops",
                "step_type": "llm",
                "aim": "Combine evidence from first three hops and determine if additional evidence is required.",
                "stage_action": (
                    "Read all retrieved passages from the first three hops. Then, answer:\n"
                    "- What facts have been established so far?\n"
                    "- What specific information is still missing to verify the claim?\n"
                    "If there are missing facts, write a concise search query to find the missing evidence.\n"
                    "If the evidence is sufficient, output exactly: ''\n"
                    "Do not output any other text."
                ),
                "reasoning_questions": (
                    "1. How do the third-hop passages address contradictions identified in earlier hops?\n"
                    "2. Do the new passages introduce any additional ambiguities or uncertainties?\n"
                    "3. After synthesizing all evidence, is there any critical gap that prevents a definitive verification of the claim?"
                ),
                "example_reasoning": (
                    "CASE 1: Evidence sufficient after three hops\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop passages:\n"
                    "  [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  [2] Paris landmarks | The tower construction started in 1889.\n"
                    "Second-hop passages:\n"
                    "  [1] Gustave Eiffel | Signed contract in 1887 and began site preparation.\n"
                    "  [2] Construction timeline | Foundation work started 1887, tower assembly began 1888.\n"
                    "Third-hop passages:\n"
                    "  [1] Engineering records | Tower structural assembly commenced February 14, 1888.\n"
                    "  [2] Historical archives | Final approval for tower construction granted January 1887.\n"
                    "Analysis:\n"
                    "  Established: Contract signed Jan 1887 (approval), foundation work began 1887, tower assembly started Feb 1888.\n"
                    "  Clarification: 'Built' is ambiguous - foundation work began in 1887 but tower structure in 1888.\n"
                    "  Sufficient: The claim 'built in 1887' is partially true (foundation) but misleading for the tower itself.\n"
                    "''\n\n"
                    "CASE 2: Evidence insufficient after three hops\n"
                    "Claim: 'The human genome was fully sequenced in 2003.'\n"
                    "First-hop passages:\n"
                    "  [1] Human Genome Project | Announced completion in 2003.\n"
                    "  [2] Genetics | The draft sequence was published in 2001.\n"
                    "Second-hop passages:\n"
                    "  [1] NIH report | Final sequencing finished in April 2003.\n"
                    "  [2] Science journal | The project was declared complete in 2003.\n"
                    "Third-hop passages:\n"
                    "  [1] Nature journal | A gap-free sequence was not achieved until 2022.\n"
                    "  [2] Genome research | The 2003 sequence had unresolved gaps.\n"
                    "Analysis:\n"
                    "  Established: The project was declared complete in 2003, but with gaps.\n"
                    "  Contradiction: Some sources say 'fully sequenced' in 2003, but recent research shows gaps remained.\n"
                    "  Missing: Clarification on what 'fully sequenced' means in the context of the 2003 announcement.\n"
                    "'Human Genome Project 2003 definition of completion'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval (if needed)
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }