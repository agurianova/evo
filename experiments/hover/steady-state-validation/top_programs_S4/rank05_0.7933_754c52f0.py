def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Always follow instructions precisely. For query generation steps, output ONLY the search query string with no additional text, formatting, or explanations.",
        "steps": [
            # Step 1: First-hop retrieval with deeper search (k=10)
            {
                "number": 1,
                "title": "Retrieve initial passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence with reasoning scaffolds
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are directly relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Space exploration | The first human spaceflight was in 1961.\n"
                    "Relevant passage: [1] states the moon landing date.\n"
                    "Key fact: Apollo 11 landed on the moon on July 20, 1969.\n"
                    "Summary: 'Apollo 11 landed on the moon on July 20, 1969.'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate primary second-hop query
            {
                "number": 3,
                "title": "Generate primary second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, determine what specific evidence is still needed to "
                    "fully verify the claim. Write a concise search query to find this missing evidence.\n"
                    "Provide ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific information is missing from the current evidence?\n"
                    "2. What search terms would most precisely retrieve this missing information?"
                ),
                "example_reasoning": (
                    "Summary: 'We have evidence that Apollo 11 landed on the moon, but the year is not specified.'\n"
                    "Missing: year of moon landing\n"
                    "moon landing year"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate alternative second-hop query
            {
                "number": 4,
                "title": "Generate alternative second-hop query",
                "step_type": "llm",
                "aim": "Identify a different missing information angle and generate a second precise search query.",
                "stage_action": (
                    "Based on the evidence summary, determine an alternative piece of evidence that would help verify the claim, "
                    "focusing on a different aspect than the primary query. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "1. What is a different gap in the evidence that hasn't been addressed by the primary query?\n"
                    "2. What search terms would most precisely retrieve this alternative evidence?"
                ),
                "example_reasoning": (
                    "Summary: 'We have evidence that Apollo 11 landed on the moon, but the year is not specified.'\n"
                    "Alternative gap: who was the commander of Apollo 11\n"
                    "Apollo 11 commander"
                ),
                "dependencies": [2],
            },
            # Step 5: Primary second-hop retrieval (k=10)
            {
                "number": 5,
                "title": "Retrieve primary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Alternative second-hop retrieval (k=10)
            {
                "number": 6,
                "title": "Retrieve alternative second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 7: Combine evidence from all hops so far (with enhanced scaffolding)
            {
                "number": 7,
                "title": "Combine evidence from first and second hops (both branches)",
                "step_type": "llm",
                "aim": "Create a unified evidence summary covering all facts from first hop and both second-hop branches.",
                "stage_action": (
                    "Integrate the first-hop evidence summary with the evidence from both second-hop retrievals. "
                    "Produce a comprehensive summary of all relevant facts gathered so far, highlighting connections between facts."
                ),
                "reasoning_questions": (
                    "1. What are the key facts from the first-hop summary?\n"
                    "2. What new facts does the primary second-hop retrieval add?\n"
                    "3. What new facts does the alternative second-hop retrieval add?\n"
                    "4. How do these facts connect to form a complete picture for verifying the claim?"
                ),
                "example_reasoning": (
                    "First-hop summary: 'Apollo 11 landed on the moon.'\n"
                    "Primary second-hop passages:\n"
                    "[1] Moon landing year | The Apollo 11 mission landed in 1969.\n"
                    "Alternative second-hop passages:\n"
                    "[1] Apollo 11 crew | Neil Armstrong was the commander of Apollo 11.\n"
                    "Key facts:\n"
                    "- Moon landing: Apollo 11\n"
                    "- Year: 1969\n"
                    "- Commander: Neil Armstrong\n"
                    "Connections: The mission (Apollo 11) landed in 1969 and was commanded by Neil Armstrong.\n"
                    "Comprehensive summary: 'Apollo 11, commanded by Neil Armstrong, landed on the moon in 1969.'"
                ),
                "dependencies": [2, 5, 6],
            },
            # Step 8: Generate third-hop query
            {
                "number": 8,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a precise search query for the third hop.",
                "stage_action": (
                    "Based on the combined evidence, determine what final piece of evidence is needed "
                    "to fully verify the claim. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific information is still missing after two hops?\n"
                    "2. What search terms would most precisely retrieve this missing information?"
                ),
                "example_reasoning": (
                    "Combined evidence: 'Apollo 11 landed on the moon on July 20, 1969.'\n"
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Missing: Neil Armstrong's role\n"
                    "Neil Armstrong first man moon"
                ),
                "dependencies": [7],
            },
            # Step 9: Third-hop retrieval with deeper search (k=10)
            {
                "number": 9,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
            # Step 10: Final evidence synthesis with enhanced gap analysis
            {
                "number": 10,
                "title": "Final evidence synthesis and gap analysis",
                "step_type": "llm",
                "aim": "Produce a final evidence summary and identify any remaining gaps.",
                "stage_action": (
                    "1. Read the third-hop passages and extract key facts relevant to the claim\n"
                    "2. Combine with the existing comprehensive evidence summary to form the final evidence set\n"
                    "3. Output a concise summary of all evidence and explicitly state any remaining gaps"
                ),
                "reasoning_questions": (
                    "1. What is the original claim?\n"
                    "2. What evidence do we have from all hops (first, second branches, and third)?\n"
                    "3. Is the evidence sufficient to verify the claim? If not, what specific information is missing?\n"
                    "4. List any remaining gaps with concrete examples of what would fill them."
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Comprehensive evidence (step7): 'Apollo 11 landed on the moon.'\n"
                    "Third-hop passages:\n"
                    "[1] 1969 events | The moon landing happened in 1969.\n"
                    "Final evidence: 'Apollo 11 landed on the moon in 1969.'\n"
                    "Gaps: None. The evidence matches the claim exactly.\n"
                    "---\n"
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Comprehensive evidence: 'Apollo 11 landed on the moon in 1969.'\n"
                    "Third-hop passages:\n"
                    "[1] Apollo 11 mission | Neil Armstrong stepped onto the moon first.\n"
                    "Final evidence: 'Neil Armstrong was the first person on the moon.'\n"
                    "Gaps: None.\n"
                    "---\n"
                    "Claim: 'The moon landing was faked.'\n"
                    "Comprehensive evidence: 'Apollo 11 landed on the moon in 1969.'\n"
                    "Third-hop passages:\n"
                    "[1] Moon landing hoax | Some conspiracy theories claim the moon landing was faked, but evidence shows it was real.\n"
                    "Final evidence: The moon landing was real and not faked.\n"
                    "Gaps: None for verification (the claim is false)."
                ),
                "dependencies": [7, 9],
            },
        ],
    }
