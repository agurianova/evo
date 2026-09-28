def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Always follow instructions precisely. For query generation steps, output ONLY the search query string with no additional text, formatting, or explanations.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve initial passages (first hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Generate primary query (second hop - direct evidence)",
                "step_type": "llm",
                "aim": "Extract key facts and identify immediate missing evidence for direct verification.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. "
                    "Determine if the claim is already verified by current evidence. "
                    "If verified, generate a query for 'additional supporting evidence for [claim]'. "
                    "If not verified, identify specific missing information to verify the claim. "
                    "Generate a single search query string covering multiple angles using OR combinations (e.g., 'term1 OR term2'). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which passages contain facts directly supporting/refuting the claim?\n"
                    "3. What key facts were extracted?\n"
                    "4. Is the claim already verified by current evidence?\n"
                    "5. If not verified, what specific information is missing?\n"
                    "6. How to phrase multiple search terms for missing evidence using OR?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Landed on moon July 20, 1969\n"
                    "[2] Crew | Included Neil Armstrong and Buzz Aldrin\n"
                    "Summary: Mission details and crew confirmed, but Armstrong's role as first person unconfirmed.\n"
                    "Claim not verified - missing: Armstrong's specific action as first to step.\n"
                    "Neil Armstrong first step moon OR first person lunar surface OR moon landing first steps"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate alternative query (second hop - contextual angles)",
                "step_type": "llm",
                "aim": "Identify alternative interpretations, related entities, or contextual information supporting the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify contextual angles (e.g., related entities, historical context). "
                    "Determine if claim is verified by current evidence. "
                    "If verified, generate query for 'alternative sources confirming [claim]'. "
                    "If not verified, identify missing contextual evidence. "
                    "Generate a single search query string with OR-combined terms for contextual gaps. "
                    "Output ONLY the search query string with no additional text."
                ),
                "reasoning_questions": (
                    "1. What related entities or contexts surround the claim?\n"
                    "2. Are there alternative interpretations needing verification?\n"
                    "3. Is claim verified by current evidence?\n"
                    "4. If not, what contextual evidence is missing?\n"
                    "5. How to phrase contextual search terms using OR?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Landed on moon July 20, 1969\n"
                    "[2] Crew | Included Neil Armstrong and Buzz Aldrin\n"
                    "Summary: Mission confirmed but no details about who stepped first.\n"
                    "Claim not verified - missing: Official records of first step.\n"
                    "NASA Apollo 11 step sequence OR lunar module exit order OR Armstrong Aldrin moonwalk sequence"
                ),
                "dependencies": [1],
            },
            {
                "number": 4,
                "title": "Retrieve primary branch (second hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 5,
                "title": "Retrieve alternative branch (second hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Merge evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Synthesize evidence from all passages, identify critical gaps, and generate precise query.",
                "stage_action": (
                    "Read all retrieved passages (initial and both second-hop branches). "
                    "Create comprehensive evidence summary. Determine verification status. "
                    "If verified, generate query for 'additional authoritative sources for [claim]'. "
                    "If not verified, identify the single most critical missing piece. "
                    "Generate a single precise search query string with OR-combined terms. "
                    "Output ONLY the search query string."
                ),
                "reasoning_questions": (
                    "1. What new evidence emerged from both branches?\n"
                    "2. How does evidence connect to original claim?\n"
                    "3. Is claim fully verified?\n"
                    "4. If not, what is the critical missing piece?\n"
                    "5. How to phrase precise search terms for this gap using OR?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages from hop1: [1][2] (mission details)\n"
                    "Passages from hop2a: [1] Armstrong first step confirmed\n"
                    "Passages from hop2b: [1] NASA step sequence records\n"
                    "Summary: Direct evidence found but lacks official timestamp.\n"
                    "Claim partially verified - missing: Exact time of first step.\n"
                    "Apollo 11 first step timestamp OR Armstrong moonwalk exact time OR NASA mission log step 1"
                ),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Evaluate completeness and generate targeted query for final gap.",
                "stage_action": (
                    "Read third-hop passages and assess evidence completeness. "
                    "If claim verified, generate query for 'definitive proof of [claim]'. "
                    "If not verified, identify the last critical missing element. "
                    "Generate a single highly focused search query string with OR terms. "
                    "Output ONLY the search query string."
                ),
                "reasoning_questions": (
                    "1. Does third-hop evidence resolve previous gaps?\n"
                    "2. Is claim now fully verified?\n"
                    "3. If not, what is the absolute last missing element?\n"
                    "4. What are the most precise search terms for this final gap?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Previous evidence: Apollo 11 landed July 20, 1969; mission ended July 24, 1969.\n"
                    "New passages: [1] Historical context | Space race concluded in 1969\n"
                    "Summary: Year confirmed but landing date specificity missing.\n"
                    "Critical gap: Confirmation that landing (not just mission) occurred in 1969.\n"
                    "Apollo 11 lunar landing date OR moon touchdown date 1969 OR July 1969 moon landing"
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Final evidence synthesis",
                "step_type": "llm",
                "aim": "Synthesize all evidence to determine verification status and coverage gaps.",
                "stage_action": (
                    "Read all retrieved passages across all hops. Create comprehensive evidence summary. "
                    "State verification status (verified/refuted/partially verified). "
                    "If incomplete, explicitly list missing elements under 'Missing:'."
                ),
                "reasoning_questions": (
                    "1. What is the complete evidence chain?\n"
                    "2. Are there contradictions?\n"
                    "3. Does evidence cover all claim elements?\n"
                    "4. What is final verification status and why?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Hop1 passages: [1][2] (mission details)\n"
                    "Hop2a passages: [1] Armstrong first step\n"
                    "Hop2b passages: [1] NASA step sequence\n"
                    "Hop3 passages: [1] July 20, 1969 02:56 UTC timestamp\n"
                    "Summary: Multiple sources confirm Armstrong as first with precise timestamp.\n"
                    "Verification: Fully verified. All claim elements supported by evidence.\n"
                    "Missing: None"
                ),
                "dependencies": [1, 4, 5, 7, 9],
            },
        ],
    }
