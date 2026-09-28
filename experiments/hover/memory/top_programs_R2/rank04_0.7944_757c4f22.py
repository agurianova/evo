def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert performing multi-hop evidence retrieval. Decompose the claim into atomic facts, retrieve evidence for each fact in sequence, and synthesize findings to identify gaps for the next hop. Each step has a specific role: initial retrieval focuses on claim entities, second-hop queries target missing relationships, and final synthesis identifies the critical gap.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve initial evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate first second-hop query (Branch A)
            {
                "number": 2,
                "title": "Generate second-hop query A",
                "step_type": "llm",
                "aim": "Identify one critical missing fact from initial evidence and generate precise search query",
                "stage_action": (
                    "Analyze the retrieved passages to determine ONE specific missing fact needed to verify the claim. "
                    "Write a concise search query that would retrieve this missing evidence. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What specific fact is currently missing to verify the claim? "
                    "Which entities or relationships in the claim are not yet supported by evidence?"
                ),
                "example_reasoning": (
                    "Example claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages mention her Nobel wins but not gender precedence. "
                    "Query: 'Was Marie Curie the first woman to win a Nobel Prize?'"),
                "dependencies": [1],
            },
            # Step 3: Generate second second-hop query (Branch B) - MODIFIED
            {
                "number": 3,
                "title": "Generate second-hop query B",
                "step_type": "llm",
                "aim": "Identify a different missing fact from initial evidence and generate alternative search query",
                "stage_action": (
                    "Analyze the retrieved passages to determine A DIFFERENT specific missing fact needed to verify the claim. "
                    "Generate a search query that retrieves complementary evidence. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What OTHER fact is missing that could support the claim? "
                    "Consider alternative perspectives or related entities that might provide evidence."
                ),
                "example_reasoning": (
                    "Example claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages mention her Nobel wins but not the historical context of women in science. "
                    "Query: 'Year of the first Nobel Prize awarded to a woman'"),
                "dependencies": [1],  # Changed from [1,2] to [1]
            },
            # Step 4: Second-hop retrieval (Branch A)
            {
                "number": 4,
                "title": "Retrieve second-hop evidence A",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},  # Step 2 output
                },
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (Branch B)
            {
                "number": 5,
                "title": "Retrieve second-hop evidence B",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},  # Step 3 output
                },
                "dependencies": [3],
            },
            # Step 6: Combine evidence and generate third-hop query
            {
                "number": 6,
                "title": "Synthesize evidence and generate final query",
                "step_type": "llm",
                "aim": "Integrate all evidence to identify final missing piece and generate third-hop query",
                "stage_action": (
                    "First, summarize the key evidence found in the initial retrieval (step1) in one sentence. "
                    "Then, summarize the key evidence from branch A (step4) and branch B (step5) separately, noting any contradictions or complementary information. "
                    "Compare the evidence from both branches to identify a specific gap that neither branch has addressed. "
                    "Write a concise search query that would retrieve evidence to fill this gap. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What key evidence was found in the initial hop? "
                    "What key evidence was found in branch A and branch B? "
                    "How do the two branches complement or contradict each other? "
                    "What specific gap remains that would confirm or refute the claim?"
                ),
                "example_reasoning": (
                    "Example: Initial hop confirms Marie Curie won Nobel Prizes. Branch A shows no female winners before 1903. Branch B shows Bertha von Suttner won Peace Prize in 1905. "
                    "Gap: No evidence about prizes before 1903. Query: 'Nobel Prize winners between 1901-1902'"),
                "dependencies": [1, 4, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve final evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},  # Step 6 output
                },
                "dependencies": [6],
            },
        ],
    }