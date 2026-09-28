def entrypoint():
    return {
        "system_prompt": "You are a multi-hop fact-checking expert. Decompose claims into atomic facts at each step. Generate precise, distinct queries that target uncovered sub-claims. Remember: Step1 retrieves basic evidence, Steps2-3 fill specific gaps with non-redundant queries, Step6 synthesizes cross-branch evidence to identify final missing pieces.",
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
            # Step 3: Generate second second-hop query (Branch B) - now depends on step2 for diversity
            {
                "number": 3,
                "title": "Generate second-hop query B",
                "step_type": "llm",
                "aim": "Identify a different missing fact from initial evidence and generate alternative search query distinct from previous query",
                "stage_action": (
                    "Analyze the retrieved passages and the previous query (from step2) to determine a DIFFERENT specific missing fact needed to verify the claim. "
                    "Write a concise search query that would retrieve this alternative missing evidence, ensuring it is distinct from the previous query. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What OTHER fact is missing that could support the claim? "
                    "How does this gap differ from the one addressed by the previous query?"
                ),
                "example_reasoning": (
                    "Example claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages mention her Nobel wins but not the historical timeline of female laureates. "
                    "Query: 'Timeline of female Nobel Prize winners in the early 1900s'"),
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
                "aim": "Integrate all evidence through structured synthesis to identify final missing piece",
                "stage_action": (
                    "1. Summarize evidence from each hop (initial, branch A, branch B) regarding claim coverage. "
                    "2. Contrast findings between branch A and branch B to identify complementary gaps. "
                    "3. Write a concise search query targeting the most critical remaining gap for verification. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What evidence has been found in each hop? "
                    "What specific gap remains in each branch that the other branch didn't cover? "
                    "Which gap is most critical for final verification?"
                ),
                "example_reasoning": (
                    "Example: Initial passages confirm Marie Curie's Nobel wins. Branch A found no female laureates before 1903. "
                    "Branch B shows Bertha von Suttner won Peace Prize in 1905. Critical gap: laureates between 1901-1903. "
                    "Query: 'Nobel Prize winners 1901 to 1903'")
                ,
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