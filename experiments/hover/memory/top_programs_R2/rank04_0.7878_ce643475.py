def entrypoint():
    return {
        "system_prompt": "You are a multi-hop fact-checking expert. Break down the claim into atomic facts and retrieve evidence step by step. Each step has a specific role:   - First retrieval: Get basic context for the claim.   - Second-hop queries: Identify and retrieve one missing fact at a time, generating distinct queries for parallel branches.   - Final synthesis: Summarize evidence per hop, contrast branches, and retrieve the final missing piece. Always output only the required information for the current step.",
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
                "aim": "Identify one atomic verifiable fact missing from initial evidence and generate precise search query",
                "stage_action": (
                    "Analyze the retrieved passages to determine ONE specific atomic verifiable fact needed to verify the claim. "
                    "Write a concise search query that would retrieve this missing evidence. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What specific atomic verifiable fact is currently missing to verify the claim? "
                    "Which entities or relationships in the claim are not yet supported by evidence? "
                    "What specific time period, location, or entity attribute is missing for this fact?"
                ),
                "example_reasoning": (
                    "Example claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages mention her Nobel wins but not gender precedence. "
                    "Atomic fact: 'Marie Curie won the Nobel Prize in Physics in 1903.' "
                    "Query: 'Marie Curie Nobel Prize Physics 1903'"),
                "dependencies": [1],
            },
            # Step 3: Generate second second-hop query (Branch B)
            {
                "number": 3,
                "title": "Generate second-hop query B",
                "step_type": "llm",
                "aim": "Identify a different atomic verifiable fact from initial evidence and generate an alternative search query that is distinct from the first query",
                "stage_action": (
                    "Analyze the retrieved passages from step1 and the first query (from step2) to determine a DIFFERENT specific atomic verifiable fact needed to verify the claim. "
                    "Write a concise search query that would retrieve this alternative missing evidence. "
                    "Ensure the query is distinct from the query generated in step2. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What specific atomic verifiable fact is currently missing that step2's query did not address? "
                    "Which entities or relationships in the claim are not yet supported by evidence from step1 and step2's query context? "
                    "What specific time period, location, or entity attribute is missing for this fact?"
                ),
                "example_reasoning": (
                    "Example claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages from step1 mention her Nobel wins but not gender precedence. "
                    "First query (step2): 'Marie Curie Nobel Prize Physics 1903' "
                    "Atomic fact: 'First woman to win a Nobel Prize' "
                    "Alternative query: 'First female Nobel Prize winner'")
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
                    "Review all retrieved passages by first summarizing the evidence found in each hop: "
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
                    "Query A (step2): 'Marie Curie Nobel Prize Physics 1903' -> retrieved passages confirm she won in 1903. "
                    "Query B (step3): 'First female Nobel Prize winner' -> retrieved passages list Bertha von Suttner as winner in 1905 (after Curie) but none before. "
                    "Contrast: Query A confirmed the year and field, Query B confirmed there were female winners after but none before. "
                    "Gap analysis by dimension: "
                    "   Time: We have evidence from 1903 and 1905, but what about before 1903? "
                    "   Location: Not applicable for this claim. "
                    "   Entities: We have Bertha von Suttner (after) but no female winner before 1903. "
                    "Final gap: Evidence of any female Nobel winner before 1903. "
                    "Query: 'Female Nobel Prize winners before 1903'")
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