def entrypoint():
    return {
        "system_prompt": "Expert fact-checker verifying claims through multi-hop evidence retrieval. Always: (1) Be precise; (2) Output ONLY requested content; (3) For summaries: bullet points of key facts/entities; (4) For queries: ONLY search string.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract all potentially relevant facts and entities from retrieved passages",
                "stage_action": "List in bullet points: (a) all facts directly supporting/contradicting the claim, (b) key entities (names, dates, locations). Preserve all details - do not interpret or conclude.",
                "reasoning_questions": "1. Which specific sentences verify elements of the claim?\n2. What entities (people, places, dates, organizations) appear in these sentences?\n3. Are there numerical values or events critical to the claim?",
                "example_reasoning": "Claim: 'Marie Curie won Nobel Prizes in 1903 and 1911'\nPassages: [0] Nobel Prize | Marie Curie won in Physics (1903) and Chemistry (1911)\n[1] Biography | First person to win two Nobels\nSummary bullets:\n- Won Nobel Prize in Physics in 1903\n- Won Nobel Prize in Chemistry in 1911\n- First person to win two Nobel Prizes\nEntities: Marie Curie, 1903, 1911, Physics, Chemistry",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify logical next evidence gap and generate focused query",
                "stage_action": "Determine what specific information is still missing to verify the claim. Create a concise, keyword-rich query targeting this gap. Output ONLY the query string.",
                "reasoning_questions": "1. Which claim element lacks sufficient evidence?\n2. What precise question would resolve this?\n3. Which 3-6 keywords best capture this need for search?",
                "example_reasoning": "Claim: 'Marie Curie won Nobels in 1903 and 1911'\nSummary: Won Physics (1903), Chemistry (1911), first two-time winner\nMissing: Confirmation she was sole winner in 1903\nQuery: 'Marie Curie 1903 Nobel Prize co-winners'",
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Integrate first-hop and second-hop evidence into unified facts",
                "stage_action": "Merge bullet points from step 2 with new evidence from step 4. Extract key facts from step 4 passages. Remove duplicates, highlight contradictions and resolve by prioritizing primary sources. Output ONLY bullet-pointed facts/entities.",
                "reasoning_questions": "1. What new facts clarify missing elements?\n2. How do they relate to existing facts?\n3. Are there conflicts requiring resolution?",
                "example_reasoning": "Step2: Won Physics (1903), Chemistry (1911)\nStep4 passages: [0] 1903 Prize | Shared with Pierre Curie and Henri Becquerel\nIntegrated bullets:\n- Won 1903 Physics Nobel with Pierre Curie and Henri Becquerel\n- Won 1911 Chemistry Nobel (solo)",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify critical missing evidence for final verification",
                "stage_action": "Identify the critical facts still missing to verify the claim. Create a comprehensive yet concise query using OR to cover multiple gaps where needed. Output ONLY the query string.",
                "reasoning_questions": "1. What facts are still missing to verify the claim?\n2. How to combine these gaps into a single query using OR where appropriate?\n3. How to phrase a comprehensive yet concise query (4-7 keywords)?",
                "example_reasoning": "Claim: 'Marie Curie won Nobels in 1903 and 1911'\nIntegrated evidence: Won 1903 (shared), 1911 (solo)\nMissing gaps: Official Nobel committee wording AND verification of solo 1911 win\nQuery: 'Nobel Prize 1903 official winner definition OR Marie Curie 1911 sole winner'",
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
                "frozen": True,
            },
        ],
    }
