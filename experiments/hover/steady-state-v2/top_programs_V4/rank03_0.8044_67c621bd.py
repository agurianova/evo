def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by gathering evidence through multiple hops of retrieval. Always be precise and avoid making assumptions. Focus on extracting and synthesizing factual evidence from retrieved passages. When generating search queries, output ONLY the query string with no additional text, formatting, or explanations. Break down complex claims into iterative sub-questions to guide evidence retrieval.",
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
            # Step 2: Extract key entities and foundational facts
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
            # Step 3: Generate first candidate query for second hop
            {
                "number": 3,
                "title": "Generate first candidate query for second hop",
                "step_type": "llm",
                "aim": "Generate the first candidate search query for the second hop to find connecting evidence.",
                "stage_action": (
                    "Based on the extracted entities and foundational facts, generate a search query that will retrieve passages connecting these entities to the claim. "
                    "The query should be appropriately specific to find the missing connecting evidence. "
                    "Output ONLY the query string, with no additional text."
                ),
                "reasoning_questions": "What is the most direct way to connect the entities from the first hop to the claim? What query would retrieve the most relevant connecting passages?",
                "example_reasoning": "The claim involves [X] and first-hop shows [Y]. Need information about [Z] that connects them. Query: 'Z relationship to X and Y'",
                "dependencies": [2],
            },
            # Step 4: Generate second candidate query for second hop
            {
                "number": 4,
                "title": "Generate second candidate query for second hop",
                "step_type": "llm",
                "aim": "Generate a second distinct candidate search query for the second hop to find connecting evidence.",
                "stage_action": (
                    "Generate a different search query that approaches the connection from another angle, such as using alternative terminology or focusing on a different relationship. "
                    "The query should be appropriately specific to find the missing connecting evidence. "
                    "Output ONLY the query string, with no additional text."
                ),
                "reasoning_questions": "What is an alternative way to phrase the connection? How might the relationship be described in a different context?",
                "example_reasoning": "Instead of 'Z relationship', consider 'how X and Y interact through Z'. Query: 'X and Y interaction mechanism via Z'",
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (first query, k=7)
            {
                "number": 5,
                "title": "Retrieve second-hop passages (first query)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Second-hop retrieval (second query, k=7)
            {
                "number": 6,
                "title": "Retrieve second-hop passages (second query)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 7: Merge second-hop passages
            {
                "number": 7,
                "title": "Merge second-hop passages",
                "step_type": "llm",
                "aim": "Merge the two sets of retrieved passages from the second hop into a single coherent set without duplicates.",
                "stage_action": (
                    "Combine the passages from the two retrievals, removing duplicates and ordering by relevance to the claim. "
                    "Output the merged list in the exact format: '[i] Title | sentence1 sentence2 ...', starting from [1]."
                ),
                "reasoning_questions": "Which passages are duplicates? How should the passages be ordered by relevance to the claim and the evidence chain?",
                "example_reasoning": "Passage [1] from first retrieval and passage [3] from second retrieval both discuss the same event, so keep one. Then order the most relevant passages first: [1] Event title | ... , [2] ... , etc.",
                "dependencies": [5, 6],
            },
            # Step 8: Extract relationships from merged second-hop
            {
                "number": 8,
                "title": "Extract relationships and connecting facts",
                "step_type": "llm",
                "aim": "Extract relationships and connecting facts from the merged second-hop passages that bridge first-hop evidence and claim.",
                "stage_action": (
                    "Read all merged second-hop passages and identify how they connect the entities/facts from the first-hop to the claim. "
                    "Focus on relationships, mechanisms, and contextual links."
                ),
                "reasoning_questions": "How do these passages specifically link the first-hop evidence to the claim through relationships or mechanisms?",
                "example_reasoning": "Passage [3] explains that [entity A] from first-hop is related to [entity B] in the claim through [mechanism]. This establishes the connection needed.",
                "dependencies": [7],
            },
            # Step 9: Generate third-hop query
            {
                "number": 9,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify precise missing evidence and generate specific query for third-hop retrieval.",
                "stage_action": (
                    "Review first-hop and second-hop evidence summaries. Identify the precise missing evidence that would further verify the claim "
                    "and write a very specific search query to find it. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is still missing to verify the claim? How can we phrase a very specific query for it?",
                "example_reasoning": "Current evidence shows [A] and [B] but lacks verification of [C]. Query: '[C] verified by [source] in [year]'",
                "dependencies": [2, 8],
            },
            # Step 10: Third-hop retrieval (k=7)
            {
                "number": 10,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }