def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by gathering evidence through multiple hops of retrieval. Always be precise and avoid making assumptions. Focus on extracting and synthesizing factual evidence from retrieved passages.",
        "steps": [
            # Step 1: First-hop retrieval (k=10)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Specialized entity extraction from first-hop
            {
                "number": 2,
                "title": "Extract key entities and foundational facts",
                "step_type": "llm",
                "aim": "Extract key entities and foundational facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify the main entities and foundational facts that directly relate to the claim. "
                    "List them concisely, focusing on entities and core facts."
                ),
                "reasoning_questions": "What are the main entities and core facts directly mentioned in these passages that relate to the claim?",
                "example_reasoning": "The claim states [claim]. Passage [1] mentions entity [X] and fact [Y] which directly relates to [claim element]. Passage [2] provides foundational context about [Z].",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (broad)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing context and generate a broad search query for connecting entities.",
                "stage_action": (
                    "Based on the first-hop summary, determine what additional context or connecting entities are needed "
                    "to link the claim to known facts. Write a concise, broad search query that will retrieve passages "
                    "about these entities or context.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What entities or concepts are missing to connect the first-hop evidence to the claim?",
                "example_reasoning": "The claim involves [X] but first-hop shows [Y]. Need information about [Z] that connects them. Query: \"Z concept and relationship to X and Y\"",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (k=10)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Specialized relationship extraction
            {
                "number": 5,
                "title": "Extract relationships and connecting facts",
                "step_type": "llm",
                "aim": "Extract relationships and connecting facts from second-hop passages that bridge first-hop evidence and claim.",
                "stage_action": (
                    "Read all second-hop retrieved passages and identify how they connect the entities/facts from the first-hop "
                    "to the claim. Focus on relationships, mechanisms, and contextual links."
                ),
                "reasoning_questions": "How do these passages specifically link the first-hop evidence to the claim through relationships or mechanisms?",
                "example_reasoning": "Passage [3] explains that [entity A] from first-hop is related to [entity B] in the claim through [mechanism]. This establishes the connection needed.",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query (always specific, no condition)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify precise missing evidence and generate specific query for third-hop retrieval.",
                "stage_action": (
                    "Review first-hop and second-hop evidence summaries. Identify the precise missing evidence that would further verify the claim "
                    "and write a very specific search query to find it.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is still missing to verify the claim? How can we phrase a very specific query for it?",
                "example_reasoning": "Current evidence shows [A] and [B] but lacks verification of [C]. Query: \"[C] verified by [source] in [year]\"",
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (k=10)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Specialized gap verification
            {
                "number": 8,
                "title": "Extract precise verification facts",
                "step_type": "llm",
                "aim": "Extract precise verification facts from third-hop passages that address specific gaps in the evidence chain.",
                "stage_action": (
                    "Read all third-hop retrieved passages and identify facts that directly fill the gap identified in the previous query generation step. "
                    "Be specific about how they verify the missing piece."
                ),
                "reasoning_questions": "Does this evidence directly fill the missing piece identified in step 6? How exactly does it verify the claim?",
                "example_reasoning": "Passage [5] directly states [missing fact] from step 6's gap analysis, confirming [claim aspect] with [source] evidence.",
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query (always ultra-specific, no condition)
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final missing verification point and generate ultra-specific query.",
                "stage_action": (
                    "Review all evidence summaries (first, second, third hops). Identify the exact missing verification point that would confirm or refute the claim "
                    "and write an extremely specific search query.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What is the final missing verification point that would confirm or refute the claim? How can we phrase an extremely specific query for it?",
                "example_reasoning": "All evidence confirms [A], [B], [C] but lacks official verification of [D]. Query: \"[Official body] statement on [D] dated [year]\"",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (k=10)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }