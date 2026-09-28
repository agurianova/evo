def entrypoint():
    return {
        "system_prompt": "Expert fact-checker verifying claims with Wikipedia. Steps 3,6: OUTPUT ONLY query - extra text breaks retrieval. Step 2: extract facts, note conflicts (no resolution). Step 5: integrate evidence, resolve conflicts using primary sources & dates. Prioritize accuracy over completeness.",
        "steps": [
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
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract claim-relevant facts from passages and note conflicts with source credibility",
                "stage_action": (
                    "1. Identify facts directly supporting or refuting the claim\n"
                    "2. Tag facts with [H1] source markers\n"
                    "3. Note conflicts and preliminary source credibility (primary/secondary)\n"
                    "4. Summarize key evidence with conflict markers"
                ),
                "reasoning_questions": "What facts support/refute the claim? Where do passages conflict? What source types provide each fact? (Do not resolve conflicts - note them for later steps)",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in 2007.\n"
                    "Retrieved passages:\n"
                    "[1] iPhone | Announced January 2007, public release June 2007\n"
                    "[2] 2007 tech | Released June 29, 2007\n"
                    "[3] Steve Jobs bio | Release delayed until July\n"
                    "Relevant facts:\n"
                    "- Announcement: January 2007 [H1-primary] (all sources)\n"
                    "- Release date conflict: June 29 [H1-primary] vs July [H1-secondary]\n"
                    "Summary: iPhone announced January 2007. Release date conflict exists between June 29 and July."
                ),
                "dependencies": [1],
                "frozen": False,
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing verification evidence and generate focused search query",
                "stage_action": (
                    "Based on the evidence summary, determine what specific information is still missing to verify the claim.\n"
                    "Write a concise search query with high information density terms to find ONLY this missing evidence.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text, explanations, or formatting.\n"
                    "Extra text will break the retrieval system."
                ),
                "reasoning_questions": "What specific information is still missing? Why is it critical for verification? How can it be found with minimal high-precision terms?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in 2007.\n"
                    "First-hop summary: iPhone announced January 2007. Release date conflict exists between June 29 and July.\n"
                    "Missing: Official public release date to resolve conflict\n"
                    "first iphone official release date"
                ),
                "dependencies": [2],
                "frozen": False,
            },
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
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Integrate first and second-hop evidence with conflict resolution",
                "stage_action": (
                    "1. Extract new facts from second-hop passages, tagging with [H2]\n"
                    "2. Integrate with first-hop summary ([H1]) into unified evidence\n"
                    "3. Resolve conflicts by: (a) prioritizing primary sources, (b) checking publication dates, (c) explaining resolution with source markers"
                ),
                "reasoning_questions": "What new [H2] facts resolve previous conflicts? How do publication dates affect credibility? Why is your resolution valid with source evidence?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in 2007.\n"
                    "First-hop summary: iPhone announced January 2007. Release date conflict: June 29 [H1-primary] vs July [H1-secondary]\n"
                    "Second-hop passages:\n"
                    "[1] Apple press release | iPhone available June 29, 2007\n"
                    "[2] TechCrunch 2007 | Launch event June 29\n"
                    "New facts: Both [H2-primary] sources confirm June 29 release\n"
                    "Conflict resolution: Press release ([H2-primary]) overrides biography ([H1-secondary]). June 29 resolution confirmed.\n"
                    "Comprehensive summary: iPhone announced January 2007 and released June 29, 2007. Claim verified."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify final verification gaps by type and generate precise search query",
                "stage_action": (
                    "Based on complete evidence, determine what single critical piece of evidence is still missing by classifying gap type (factual/contextual/temporal).\n"
                    "Write a highly focused search query using minimal terms needed (typically 3-7) based on claim complexity.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text - extra text breaks retrieval.\n"
                    "Note: This triggers a deep search (k=10), so maximize precision to filter irrelevant results."
                ),
                "reasoning_questions": "What final gap prevents full verification? Is it factual, contextual, or temporal? Why is this information irreplaceable? How many precise terms are needed to capture this gap?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Einstein won Nobel for relativity\n"
                    "Current evidence: Won 1921 Nobel for photoelectric effect, not relativity\n"
                    "Missing: Official Nobel citation text (factual gap)\n"
                    "einstein 1921 nobel prize citation"
                ),
                "dependencies": [5],
                "frozen": False,
            },
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
