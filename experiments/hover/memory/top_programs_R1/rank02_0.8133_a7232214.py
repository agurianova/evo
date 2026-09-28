def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. Focus on finding objective, factual evidence and avoid speculation. Always anchor your reasoning to the original claim. For multi-hop claims, break down verification into distinct sub-questions. Generate focused search queries targeting specific missing evidence. When generating multiple queries, ensure they cover complementary facets to maximize coverage. Always generate a third-hop query to find additional supporting documents even if the claim appears verified.",
        "steps": [
            {
                "number": 1,
                "title": "First-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence and generate a focused search query for it.",
                "stage_action": "Output exactly one search query string targeting the most critical missing evidence. Do not output any other text or formatting.",
                "reasoning_questions": "1. What is the single most important missing fact for verification?\n2. How can I phrase a precise query for this missing fact?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "First-hop evidence: The Eiffel Tower was built in Paris for the 1889 World's Fair. Gustave Eiffel's company designed it.\n"
                    "Missing evidence: Where was the tower originally intended to be built?\n"
                    "Query: 'Eiffel Tower original intended location'\n\n"

                    "Claim: 'Photosynthesis produces oxygen as a byproduct.'\n"
                    "First-hop evidence: Photosynthesis converts light energy to chemical energy using carbon dioxide and water.\n"
                    "Missing evidence: What are the specific outputs/byproducts?\n"
                    "Query: 'photosynthesis byproducts oxygen'"),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different critical missing evidence facet and generate a complementary search query that does not overlap with the first query.",
                "stage_action": "Output exactly one search query string targeting a distinct missing evidence aspect. Do not output any other text or formatting. Ensure the query is meaningfully different from the first query.",
                "reasoning_questions": "1. What is another key missing fact not covered by the first query?\n2. How can I phrase a precise query for this alternative facet without overlapping evidence?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "First-hop evidence: The Eiffel Tower was built in Paris for the 1889 World's Fair. Gustave Eiffel's company designed it.\n"
                    "First query: 'Eiffel Tower original intended location'\n"
                    "Missing evidence: What other cities were considered during planning?\n"
                    "Query: 'Eiffel Tower alternative locations considered'\n\n"

                    "Claim: 'Photosynthesis produces oxygen as a byproduct.'\n"
                    "First-hop evidence: Photosynthesis converts light energy to chemical energy using carbon dioxide and water.\n"
                    "First query: 'photosynthesis byproducts oxygen'\n"
                    "Missing evidence: What is the complete chemical equation?\n"
                    "Query: 'photosynthesis chemical equation'")
            },
            {
                "number": 4,
                "title": "First second-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 5,
                "title": "Second second-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Synthesize all evidence gathered and generate a query for additional supporting documents to maximize coverage",
                "stage_action": (
                    "Review all evidence (first-hop and both second-hop results). "
                    "Output exactly one search query string targeting the next most relevant evidence for coverage. "
                    "Always generate a query - do not skip third-hop retrieval."
                ),
                "reasoning_questions": (
                    "1. What evidence has been gathered from all prior retrievals?\n"
                    "2. What remaining gaps exist in the document coverage?\n"
                    "3. How can I formulate a query for the most relevant additional evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie was the first woman to win a Nobel Prize, and she won it in Physics.'\n"
                    "First-hop evidence: Marie Curie won Nobel Prizes in Physics (1903) and Chemistry (1911). She was the first woman to win a Nobel Prize.\n"
                    "Second-hop evidence (query1): Marie Curie was the first woman to win a Nobel Prize (1903).\n"
                    "Second-hop evidence (query2): She won in Physics and Chemistry.\n"
                    "Coverage gap: Details about other early female Nobel laureates to confirm 'first' status\n"
                    "Query: 'early female Nobel Prize winners before Marie Curie'\n\n"

                    "Claim: 'The Berlin Wall fell in 1989, leading to German reunification in 1990.'\n"
                    "First-hop evidence: The Berlin Wall fell in 1989. German reunification occurred on 3 October 1990.\n"
                    "Second-hop evidence (query1): The fall happened in November 1989.\n"
                    "Second-hop evidence (query2): Reunification date confirmed as 3 October 1990.\n"
                    "Coverage gap: International reactions to the fall\n"
                    "Query: 'international response to Berlin Wall fall 1989'"),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 7,
                "title": "Third-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }