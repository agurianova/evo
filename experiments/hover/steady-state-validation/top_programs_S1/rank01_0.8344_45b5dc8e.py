def entrypoint():
    return {
        "system_prompt": "You are a fact-checker. Be precise: output ONLY the query when instructed to generate a search query.",
        "steps": [
            # Step 1: First-hop retrieval with high recall
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
            # Step 2: Summarize first-hop evidence and identify two gaps
            {
                "number": 2,
                "title": "Summarize first-hop evidence and identify two gaps",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop passages and explicitly identify two missing pieces of evidence needed to verify the claim.",
                "stage_action": (
                    "Read the retrieved passages and summarize the key facts. Then, state exactly two specific gaps in the evidence "
                    "(what is still missing to fully verify the claim). Format: 'Gap 1: [description]; Gap 2: [description]'"
                ),
                "reasoning_questions": (
                    "What has been verified by the first-hop evidence? "
                    "What are two critical facts still missing to confirm the claim?"
                ),
                "example_reasoning": (
                    "Claim: [CLAIM]\n"
                    "First-hop evidence: [SUMMARY]\n"
                    "Gap 1: [GAP1]; Gap 2: [GAP2]"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for Gap 1
            {
                "number": 3,
                "title": "Generate query for Gap 1",
                "step_type": "llm",
                "aim": "Generate a search query to find evidence for Gap 1 identified in step 2.",
                "stage_action": (
                    "Based on Gap 1 description, write a concise search query to retrieve evidence that would fill this gap. "
                    "Output ONLY the query string, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing? "
                    "What keywords would appear in a document containing this fact?"
                ),
                "example_reasoning": (
                    "Claim: [CLAIM]\n"
                    "First-hop evidence: [SUMMARY]\n"
                    "Gap 1: [GAP1]\n"
                    "Query: [QUERY]"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate query for Gap 2
            {
                "number": 4,
                "title": "Generate query for Gap 2",
                "step_type": "llm",
                "aim": "Generate a search query to find evidence for Gap 2 identified in step 2.",
                "stage_action": (
                    "Based on Gap 2 description, write a concise search query to retrieve evidence that would fill this gap. "
                    "Output ONLY the query string, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing? "
                    "What keywords would appear in a document containing this fact?"
                ),
                "example_reasoning": (
                    "Claim: [CLAIM]\n"
                    "First-hop evidence: [SUMMARY]\n"
                    "Gap 2: [GAP2]\n"
                    "Query: [QUERY]"
                ),
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval for Gap 1
            {
                "number": 5,
                "title": "Retrieve second-hop passages for Gap 1",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},  # Step 3 output
                },
                "dependencies": [3],
            },
            # Step 6: Second-hop retrieval for Gap 2
            {
                "number": 6,
                "title": "Retrieve second-hop passages for Gap 2",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},  # Step 4 output
                },
                "dependencies": [4],
            },
            # Step 7: Summarize all evidence and identify one gap
            {
                "number": 7,
                "title": "Summarize all evidence and identify one gap",
                "step_type": "llm",
                "aim": "Integrate evidence from all retrieved passages and identify the single most critical remaining gap in evidence.",
                "stage_action": (
                    "Combine the evidence from the first hop (step1) and both second hops (step5 and step6) into a comprehensive summary. "
                    "Then, state the single most important piece of evidence still missing to verify the claim. "
                    "Format: 'Remaining Gap: [description]'"
                ),
                "reasoning_questions": (
                    "What has been verified so far? "
                    "What is the one key fact still missing that would make the verification conclusive?"
                ),
                "example_reasoning": (
                    "Claim: [CLAIM]\nEvidence: [SUMMARY OF ALL]\nRemaining Gap: [GAP]"
                ),
                "dependencies": [1, 5, 6],
            },
            # Step 8: Generate query for the remaining gap
            {
                "number": 8,
                "title": "Generate query for the remaining gap",
                "step_type": "llm",
                "aim": "Generate a search query to find evidence for the remaining gap identified in step 7.",
                "stage_action": (
                    "Based on the remaining gap description, write a concise search query to retrieve evidence that would fill this gap. "
                    "Output ONLY the query string, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing? "
                    "What keywords would appear in a document containing this fact?"
                ),
                "example_reasoning": (
                    "Claim: [CLAIM]\n"
                    "Evidence: [SUMMARY]\n"
                    "Remaining Gap: [GAP]\n"
                    "Query: [QUERY]"
                ),
                "dependencies": [7],
            },
            # Step 9: Third-hop retrieval
            {
                "number": 9,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},  # Step 8 output
                },
                "dependencies": [8],
            },
        ],
    }
