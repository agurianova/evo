def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert specializing in multi-hop evidence retrieval. Break down the claim into atomic facts and retrieve evidence step-by-step. Each step has a specific role:\n- Step 1: Retrieve initial evidence about the claim's main entities.\n- Steps 2-3: Generate distinct second-hop queries targeting missing relationships (step2: primary gap, step3: alternative gap).\n- Steps 4-5: Retrieve second-hop evidence for each query.\n- Step 6: Synthesize evidence across branches to identify precise gaps for final retrieval.\n- Step 7: Retrieve the final missing evidence.\nAlways output only the required element (e.g., search queries) without extra text.",
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
            # Step 3: Generate second second-hop query (Branch B)
            {
                "number": 3,
                "title": "Generate second-hop query B",
                "step_type": "llm",
                "aim": "Identify a different missing fact from initial evidence and generate alternative search query",
                "stage_action": (
                    "Analyze the initial evidence (step1) and the first query (step2) to identify a missing fact that is DIFFERENT from step2's target. "
                    "Write a concise search query for this alternative missing evidence. "
                    "Ensure the query is distinct from the previous query. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What OTHER fact is missing that could support the claim? "
                    "How does this gap differ from the one targeted by step2? "
                    "Which entities in this alternative gap are most searchable?"
                ),
                "example_reasoning": (
                    "Example claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages confirm her Nobel wins but do not mention the year of the first Nobel Prize. "
                    "Query: 'Year of the first Nobel Prize ceremony'"),
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
                "aim": "Integrate all evidence to identify final missing piece and generate third-hop query",
                "stage_action": (
                    "1. Summarize the key evidence found in the initial retrieval (step1) in one sentence.\n"
                    "2. Summarize the key evidence from second-hop branch A (step4) in one sentence.\n"
                    "3. Summarize the key evidence from second-hop branch B (step5) in one sentence.\n"
                    "4. Compare the three summaries to identify the precise missing piece of evidence.\n"
                    "5. Write a concise search query for this final missing evidence. \n"
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What key facts are established by the initial evidence? \n"
                    "What new facts were added by branch A? By branch B? \n"
                    "What critical gap remains when combining all evidence? \n"
                    "Which entity or relationship in this gap is most searchable?"
                ),
                "example_reasoning": (
                    "Example: \n"
                    "Step1 summary: Marie Curie won Nobel Prizes in Physics (1903) and Chemistry (1911).\n"
                    "Step4 summary: The first Nobel Prize was awarded in 1901.\n"
                    "Step5 summary: Bertha von Suttner won the Peace Prize in 1905.\n"
                    "Gap: No evidence about female laureates before 1903. \n"
                    "Query: 'Female Nobel Prize winners before 1903'")
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