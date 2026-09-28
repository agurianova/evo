def entrypoint():
    return {
        "system_prompt": "You are a multi-hop fact-checking expert. Break down the claim into atomic verifiable units and retrieve evidence step by step. Each step has a specific role:   - First retrieval: Get basic context for the claim.   - Second-hop queries: Identify and retrieve evidence for one atomic verifiable unit at a time, generating distinct queries for parallel branches.   - Final synthesis: Summarize evidence per hop, contrast branches, and retrieve the final missing piece. Always output only the required information for the current step.",
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
                "aim": "Break the claim into atomic verifiable units. Identify the first atomic unit that is not supported by the initial evidence and generate a precise search query for it.",
                "stage_action": (
                    "Analyze the retrieved passages to determine ONE specific atomic verifiable unit needed to verify the claim. "
                    "Write a concise search query that would retrieve evidence for this unit. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What specific atomic verifiable unit is currently missing to verify the claim? "
                    "Which entities or relationships in the claim are not yet supported by evidence? "
                    "What specific time period, location, or entity attribute is missing?"
                ),
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'Marie Curie was the first woman to win a Nobel Prize.' \n"
                    "Passages mention her Nobel wins but not gender precedence. \n"
                    "Query: 'Was Marie Curie the first woman to win a Nobel Prize?'\n\n"
                    "Example 2:\n"
                    "Claim: 'The 1954 Geneva Conference resulted in the partition of Vietnam at the 17th parallel.' \n"
                    "Passages mention the conference and partition but not the parallel. \n"
                    "Query: 'What parallel was used to partition Vietnam after the 1954 Geneva Conference?'")
                ,
                "dependencies": [1],
            },
            # Step 3: Generate second second-hop query (Branch B)
            {
                "number": 3,
                "title": "Generate second-hop query B",
                "step_type": "llm",
                "aim": "Break the claim into atomic verifiable units. Identify a second distinct atomic verifiable unit that is not supported by the initial evidence and generate a precise search query for it.",
                "stage_action": (
                    "Analyze the retrieved passages from step1 and the first query (from step2) to determine a DIFFERENT specific atomic verifiable unit needed to verify the claim. "
                    "Write a concise search query that would retrieve evidence for this unit. "
                    "Ensure the query is distinct from the query generated in step2. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What specific atomic verifiable unit is currently missing that step2's query did not address? "
                    "Which entities or relationships in the claim are not yet supported by evidence from step1 and step2's query context? "
                    "What specific time period, location, or entity attribute is missing?"
                ),
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'Marie Curie was the first woman to win a Nobel Prize.' \n"
                    "Passages from step1 mention her Nobel wins but not gender precedence. \n"
                    "First query (step2): 'Was Marie Curie the first woman to win a Nobel Prize?' \n"
                    "Alternative query: 'List of female Nobel Prize winners before Marie Curie'\n\n"
                    "Example 2:\n"
                    "Claim: 'The 1954 Geneva Conference resulted in the partition of Vietnam at the 17th parallel.' \n"
                    "Passages from step1 mention the conference and partition but not the year or the parallel number. \n"
                    "First query (step2): 'What parallel was used to partition Vietnam after the 1954 Geneva Conference?' \n"
                    "Alternative query: 'When did the 1954 Geneva Conference take place?'")
                ,
                "dependencies": [1, 2],
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
                "aim": "Integrate evidence from all hops to identify final missing piece and generate third-hop query",
                "stage_action": (
                    "Review the search queries generated in step2 and step3 and the retrieved passages from all hops. "
                    "First, summarize the evidence found in each hop: "
                    "  - Initial retrieval (step1): [summarize key points] "
                    "  - Second-hop branch A (step4): [summarize key points] "
                    "  - Second-hop branch B (step5): [summarize key points] "
                    "Then, contrast the evidence from branch A and branch B to identify complementary gaps. "
                    "Determine the final missing piece of evidence needed for verification. "
                    "Write a concise search query that would retrieve the final missing evidence. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What evidence has been found in each hop? "
                    "How do the findings from branch A and branch B complement or contradict each other? "
                    "What specific gap remains that would confirm or refute the claim? "
                    "Which entities in this gap are most searchable? "
                    "Systematically check time, location, and entities covered to identify gaps."
                ),
                "example_reasoning": (
                    "Example: Initial passages (step1) confirm Marie Curie won Nobel Prizes. "
                    "Branch A (step4): shows she won two Nobel Prizes but doesn't address gender precedence. "
                    "Branch B (step5): lists female laureates after her but none before. "
                    "Contrast: Neither branch provides evidence of female laureates before her. "
                    "Query: 'Who was the first woman to win a Nobel Prize?'")
                ,
                "dependencies": [1, 2, 3, 4, 5],
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