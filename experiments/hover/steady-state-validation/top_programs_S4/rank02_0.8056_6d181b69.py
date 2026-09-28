def entrypoint():
    return {
        "system_prompt": "You are an expert evidence retrieval assistant for claim verification. Follow the instructions for each step precisely.\n\n- In steps that generate a search query: output ONLY the search query string, with no additional text, explanations, or formatting. CRITICAL: Any extra text will break the pipeline.\n- In steps that summarize evidence: output a concise bullet-point list of key facts relevant to the claim, without any extra commentary.\n- If evidence from different sources contradicts, identify the conflict and generate queries to resolve it.\n\nAlways be precise and avoid extraneous text.",
        "steps": [
            # Step 1: First-hop retrieval with deep search (k=10)
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
            # Step 2: Summarize first-hop evidence with gap prioritization
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key entities/events/properties and prioritize gaps for second-hop",
                "stage_action": "Read retrieved passages and identify main entities, events, and their properties (dates, locations, numbers). Then list specific evidence gaps requiring second-hop retrieval, ordered by criticality for claim verification. Output bullet-point facts and prioritized gaps without commentary.",
                "reasoning_questions": "What are main entities/events?\nWhat properties (dates/numbers/locations) are stated?\nWhich gaps are most critical for verification?",
                "example_reasoning": "Example 1 (Sports):\nClaim: 'Usain Bolt set the 100m world record in 2009.'\nPassages:\n[1] Usain Bolt | Set world record of 9.58 seconds at 2009 World Championships in Berlin.\nRelevant facts:\n- World record time: 9.58 seconds\n- Event: 2009 World Championships\n- Location: Berlin\nGaps (by criticality):\n1. Exact date of the record\n2. Official ratification date\n\nExample 2 (Politics):\nClaim: 'The Brexit referendum was held in 2017.'\nPassages:\n[1] Brexit referendum | Held on June 23, 2016, resulting in vote to leave EU.\nRelevant facts:\n- Date: June 23, 2016\n- Outcome: Leave\nGaps (by criticality):\n1. Official referendum date",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (critical path)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify top-priority missing evidence and generate precise query",
                "stage_action": "Based on prioritized gaps, determine most critical missing evidence and write concise search query. Output ONLY the query string. WARNING: Output must be exactly the query with no additional text.",
                "reasoning_questions": "What is the #1 critical gap?\nWhat specific information resolves it?",
                "example_reasoning": "Usain Bolt 100m world record date\n\nBrexit referendum official date",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval with deep search (k=10)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence with gap prioritization
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract relationships and prioritize remaining gaps for third-hop",
                "stage_action": "Read retrieved passages to identify how evidence connects to prior facts. Highlight confirmations/contradictions and list remaining gaps by criticality for claim verification. Output bullet-point facts and prioritized gaps without commentary.",
                "reasoning_questions": "How does this evidence relate to first-hop facts?\nAre there contradictions?\nWhat gaps remain (ordered by criticality)?",
                "example_reasoning": "Example 1 (Sports):\nClaim: 'Usain Bolt set the 100m world record in 2009.'\nFirst-hop summary:\n- World record: 9.58s\n- Event: 2009 World Championships\nSecond-hop passages:\n[1] Athletics Archives | Record set on August 16, 2009 in Berlin.\nRelevant facts:\n- Date: August 16, 2009\n- Location: Berlin\nGaps (by criticality):\n1. Official ratification date\n\nExample 2 (Science):\nClaim: 'Water boils at 100°C at sea level.'\nFirst-hop summary:\n- Boiling point at 1 atm: 100°C\nSecond-hop passages:\n[1] Altitude Physics | Boiling point decreases 1°C per 300m altitude gain.\nRelevant facts:\n- Sea level = 0m altitude\n- Confirms claim condition\nGaps (by criticality):\n1. None for sea level condition",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify top-priority missing evidence and generate precise query",
                "stage_action": "Based on prioritized gaps, determine most critical missing evidence and write concise search query. Output ONLY the query string. WARNING: Output must be exactly the query with no additional text.",
                "reasoning_questions": "What is the #1 critical gap?\nWhat specific information resolves it?",
                "example_reasoning": "Usain Bolt world record official ratification date\n\nNIST standard boiling point documentation",
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval with deep search (k=10)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence with gap prioritization
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract conclusive evidence and identify final gaps for fourth-hop",
                "stage_action": "Read retrieved passages to determine if claim can be verified. Identify any remaining critical gaps requiring fourth-hop retrieval, ordered by verification necessity. Output bullet-point conclusions and prioritized gaps without commentary.",
                "reasoning_questions": "What conclusive evidence exists?\nAre contradictions resolved?\nWhat single gap remains most critical for verification?",
                "example_reasoning": "Example 1 (Sports):\nClaim: 'Usain Bolt set the 100m world record in 2009.'\nFirst/second-hop summaries:\n- Record set August 16, 2009\n- Gap: Ratification date\nThird-hop passages:\n[1] IAAF Bulletin | Record ratified on August 21, 2009.\nConclusive facts:\n- Ratification date: August 21, 2009\nGaps (by criticality):\n1. None\n\nExample 2 (Politics):\nClaim: 'The Brexit referendum was held in 2017.'\nFirst/second-hop summaries:\n- Date: June 23, 2016\n- Gap: Official documentation\nThird-hop passages:\n[1] UK Parliament | Referendum held June 23, 2016 per Electoral Commission report.\nConclusive facts:\n- Official date confirmed as June 23, 2016\nGaps (by criticality):\n1. None",
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final critical gap and generate precise query",
                "stage_action": "Based on gap analysis, determine if one critical gap remains and write concise search query. Output ONLY the query string. WARNING: Output must be exactly the query with no additional text.",
                "reasoning_questions": "Is there one critical unresolved gap?\nWhat specific query resolves it?",
                "example_reasoning": "IAAF world record ratification process 2009\n\nBrexit referendum legal documentation",
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval with deep search (k=10)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }
