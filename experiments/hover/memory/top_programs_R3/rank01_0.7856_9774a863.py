def entrypoint():
    return {
        "system_prompt": (
            "You are a meticulous fact-checker verifying claims using multi-hop evidence retrieval. "
            "Your goal is to retrieve all relevant evidence to verify the claim by performing necessary retrieval hops. "
            "When generating a search query, output ONLY the query string with no additional text. "
            "When summarizing evidence, be concise and factual, focusing on information directly relevant to the claim."
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
            # Step 2: Summarize first-hop evidence (enhanced)
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract ALL key facts from retrieved passages relevant to claim verification.",
                "stage_action": (
                    "Read all retrieved passages and identify ALL facts that are relevant "
                    "to verifying the claim. Do not omit any detail that might be critical, "
                    "including specific dates, numbers, and contextual details. "
                    "Summarize the evidence found, highlighting any contradictions."
                ),
                "reasoning_questions": (
                    "1. What is the main subject of the claim?\n"
                    "2. Which facts in the retrieved passages directly relate to the claim?\n"
                    "3. Are there any contradictions or inconsistencies in the evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Retrieved passages:\n"
                    "  [1] Eiffel Tower | Construction began in January 1887 and was completed in March 1889.\n"
                    "  [2] Paris Landmarks | The Eiffel Tower's construction started in July 1889.\n"
                    "Summary: Passage 1 states construction began in January 1887 and ended in March 1889, while passage 2 claims construction started in July 1889. This contradiction requires further investigation."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (enhanced examples)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate search query for second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific information is missing from the first-hop evidence to verify the claim?\n"
                    "2. What entities or events should be searched for to find the missing information?\n"
                    "3. How should contradictions in the evidence be resolved?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Summary: Passage 1 states construction began in January 1887 (ended March 1889), passage 2 claims started July 1889.\n"
                    "Missing: Contradiction between 1887 and 1889 start dates requires authoritative resolution.\n"
                    "Query: 'Eiffel Tower construction start date official records'\n\n"
                    "Claim: 'Albert Einstein developed the theory of relativity in 1905.'\n"
                    "Summary: Multiple sources confirm Einstein published special relativity in 1905, but none specify the exact month.\n"
                    "Missing: Precise publication timeline for verification.\n"
                    "Query: 'Einstein special relativity publication date'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence (enhanced)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract ALL key facts from second-hop passages relevant to claim verification.",
                "stage_action": (
                    "Read all retrieved passages and identify ALL facts that are relevant "
                    "to verifying the claim. Do not omit any detail that might be critical, "
                    "including specific dates, numbers, and contextual details. "
                    "Summarize the evidence found, highlighting any contradictions."
                ),
                "reasoning_questions": (
                    "1. Which facts address the missing information from the first hop?\n"
                    "2. Do these passages resolve previous contradictions?\n"
                    "3. Are there new contradictions with existing evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop summary: Construction began Jan 1887 (passage1) vs July 1889 (passage2).\n"
                    "Retrieved passages:\n"
                    "  [1] Gustave Eiffel Archives | Foundation stone laid January 28, 1887; construction progressed through 1888-1889.\n"
                    "Summary: Official records confirm construction began January 28, 1887, resolving the contradiction (passage2 was incorrect)."
                ),
                "dependencies": [4],
            },
            # Step 6: Integrate evidence and analyze gaps (enhanced examples)
            {
                "number": 6,
                "title": "Integrate evidence and analyze gaps",
                "step_type": "llm",
                "aim": "Combine evidence from both hops and determine if additional evidence is needed.",
                "stage_action": (
                    "Read the first-hop evidence summary and the second-hop evidence summary. Then, answer:\n"
                    "- What facts have been established?\n"
                    "- What specific information is still missing to verify the claim?\n"
                    "If there are missing facts, write a concise search query to find the missing evidence.\n"
                    "If the evidence is sufficient, output exactly: 'NO_HOP_NEEDED'.\n"
                    "Do not output any other text."
                ),
                "reasoning_questions": (
                    "1. What key facts are present in the first-hop summary?\n"
                    "2. What key facts are present in the second-hop summary?\n"
                    "3. What specific fact is missing to verify the claim? (If none, state 'None')\n"
                    "4. How were contradictions resolved (if any)?"
                ),
                "example_reasoning": (
                    "Example 1 (needs third hop):\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  First-hop summary: Construction began Jan 1887 (passage1) vs July 1889 (passage2).\n"
                    "  Second-hop summary: Foundation stone laid January 28, 1887, confirming start year.\n"
                    "  Analysis: The evidence confirms construction began in 1887, but we need to verify if 'built' refers to completion (1889) or start.\n"
                    "  Query: 'Eiffel Tower built year definition'\n\n"
                    "Example 2 (sufficient evidence):\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  First-hop summary: Construction began Jan 1887 (passage1) vs July 1889 (passage2).\n"
                    "  Second-hop summary: Historical consensus confirms construction started January 1887.\n"
                    "  Analysis: The evidence resolves the contradiction and confirms construction began in 1887.\n"
                    "  NO_HOP_NEEDED\n\n"
                    "Example 3 (contradictory evidence):\n"
                    "  Claim: 'Mount Everest's height is 8848 meters.'\n"
                    "  First-hop summary: Official records state 8848m (1955), but recent survey suggests 8849m.\n"
                    "  Second-hop summary: Chinese survey 2020 confirms 8848.86m, while Nepal uses 8847.73m.\n"
                    "  Analysis: Contradiction between countries' measurements requires authoritative source.\n"
                    "  Query: 'Mount Everest official height international agreement'"
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (conditional)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }