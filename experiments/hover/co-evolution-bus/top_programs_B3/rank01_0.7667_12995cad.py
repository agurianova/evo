def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims using Wikipedia evidence. In query generation steps (3,6), output ONLY the search query with no additional text - extra text breaks retrieval. For summarization steps: step 2 extracts facts and notes conflicts without resolution; step 5 integrates evidence and resolves conflicts by prioritizing primary sources and checking publication dates. Always prioritize factual accuracy over completeness when conflicts exist.",
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
                "aim": "Extract claim-relevant facts from passages and note conflicts without resolution",
                "stage_action": (
                    "1. Identify facts directly supporting or refuting the claim\n"
                    "2. Note any conflicting facts (e.g., contradictory dates/statements)\n"
                    "3. Summarize key evidence with conflict markers"
                ),
                "reasoning_questions": "What facts support/refute the claim? Where do passages conflict? (Do not resolve conflicts - note them for later steps)",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in 2007.\n"
                    "Retrieved passages:\n"
                    "[1] iPhone | Announced January 2007, public release June 2007\n"
                    "[2] 2007 tech | Released June 29, 2007\n"
                    "[3] Steve Jobs bio | Release delayed until July\n"
                    "Relevant facts:\n"
                    "- Announcement: January 2007 (all sources)\n"
                    "- Release date conflict: June 29 (passage 2) vs July (passage 3)\n"
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
                    "Write a concise search query to find ONLY this missing evidence.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text, explanations, or formatting.\n"
                    "Extra text will break the retrieval system."
                ),
                "reasoning_questions": "What specific information is still missing? Why is it critical for verification? How can it be found with minimal query terms?",
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
                    "1. Extract new facts from second-hop passages relevant to the claim\n"
                    "2. Integrate with first-hop summary into unified evidence\n"
                    "3. Resolve conflicts by: (a) prioritizing primary sources (official records), (b) checking publication dates, (c) explaining resolution"
                ),
                "reasoning_questions": "What new facts resolve previous conflicts? How do publication dates affect source credibility? Why is your resolution valid?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in 2007.\n"
                    "First-hop summary: iPhone announced January 2007. Release date conflict: June 29 vs July.\n"
                    "Second-hop passages:\n"
                    "[1] Apple press release | iPhone available June 29, 2007\n"
                    "[2] TechCrunch 2007 | Launch event June 29\n"
                    "New facts: Both sources confirm June 29 release\n"
                    "Conflict resolution: Press release (primary source) and contemporaneous report override biography (secondary source). June 29 resolution confirmed.\n"
                    "Comprehensive summary: iPhone announced January 2007 and released June 29, 2007. Claim verified."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify final verification gaps and generate precise search query",
                "stage_action": (
                    "Based on complete evidence, determine what single critical piece of evidence is still missing.\n"
                    "Write a highly focused search query to find ONLY this evidence.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text - extra text breaks retrieval.\n"
                    "Note: This triggers a deep search (k=10), so maximize precision to filter irrelevant results."
                ),
                "reasoning_questions": "What final gap prevents full verification? Why is this specific information irreplaceable? How can it be queried in ≤5 terms?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Einstein won Nobel for relativity\n"
                    "Current evidence: Won 1921 Nobel for photoelectric effect, not relativity\n"
                    "Missing: Official Nobel citation text\n"
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
