def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Your task is to retrieve ALL passages necessary to verify the claim through multi-hop retrieval. At each step, analyze current evidence to identify precise missing information, then generate ONLY the search query needed to find it.",
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing evidence and generate precise query for second hop",
                "stage_action": (
                    "Analyze the retrieved passages to determine what specific information is still missing to verify the claim. "
                    "Write a concise search query targeting ONLY the missing evidence. "
                    "Provide ONLY the search query text, no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What key fact from the claim remains unverified by current evidence?\n"
                    "2. Which entities/events in the claim could lead to the missing evidence?\n"
                    "3. How can we phrase a query that isolates the missing information?"
                ),
                "example_reasoning": (
                    "Example for claim 'The Eiffel Tower was originally intended to be temporary':\n"
                    "- Passages show it was scheduled for demolition (temporary) but don't explain preservation reason\n"
                    "- Missing: why demolition was canceled\n"
                    "- Entities: Eiffel Tower, Gustave Eiffel, 1909\n"
                    "- Query: 'why Eiffel Tower not demolished after 1909'"
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
            # Step 4: Generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate precise query for third hop",
                "stage_action": (
                    "Analyze ALL evidence gathered so far (including previous hops) to determine what specific information is still missing. "
                    "Write a concise search query targeting ONLY the missing evidence. "
                    "Provide ONLY the search query text, no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What claim element remains unverified after combining all evidence?\n"
                    "2. Which new entities from second hop could bridge the gap?\n"
                    "3. How to phrase a query that avoids previously retrieved information?"
                ),
                "example_reasoning": (
                    "Example for claim 'Photosynthesis produces oxygen as a byproduct':\n"
                    "- First hop: confirms oxygen production but not biochemical mechanism\n"
                    "- Second hop: shows chloroplast role but misses electron transport chain\n"
                    "- Missing: specific process step creating oxygen\n"
                    "- Query: 'which step of photosynthesis releases oxygen'"
                ),
                "dependencies": [3],
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
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final evidence gaps and generate precise query for fourth hop",
                "stage_action": (
                    "Analyze COMPLETE evidence set to determine if ANY claim element remains unverified. "
                    "If gaps exist, write a query targeting ONLY the missing evidence. If sufficient, output 'SUFFICIENT'. "
                    "Provide ONLY the query or 'SUFFICIENT', no additional text."
                ),
                "reasoning_questions": (
                    "1. Does current evidence fully verify EVERY claim component?\n"
                    "2. What is the LAST missing piece if any?\n"
                    "3. How to phrase the most targeted query for the final gap?"
                ),
                "example_reasoning": (
                    "Example for claim 'Vitamin C prevents scurvy':\n"
                    "- First hop: links scurvy to vitamin deficiency\n"
                    "- Second hop: shows citrus prevents scurvy\n"
                    "- Third hop: confirms vitamin C is in citrus\n"
                    "- All elements verified → Output: 'SUFFICIENT'"
                ),
                "dependencies": [5],
            },
            # Step 7: Fourth-hop retrieval
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