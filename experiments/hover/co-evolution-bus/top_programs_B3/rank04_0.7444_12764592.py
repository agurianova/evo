def entrypoint():
    return {
        "system_prompt": "Fact-checker: Steps 3/6 output ONLY query. Step 2: extract facts & note conflicts. Step 5: resolve conflicts. Prioritize accuracy.",
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
                "reasoning_questions": "What facts support/refute the claim? Where do passages conflict? (Do not resolve conflicts - note them for later steps). For temporal claims: what is the sequence of events?",
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
                    "1. Extract new facts from second-hop passages and tag with [H2]\n"
                    "2. Integrate with first-hop summary (tagged [H1])\n"
                    "3. Resolve conflicts by: (a) source credibility (proximity, expertise, corroboration), (b) publication dates, (c) explaining resolution"
                ),
                "reasoning_questions": "What new facts resolve previous conflicts? How do publication dates affect credibility? Why is your resolution valid?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in 2007.\n"
                    "First-hop summary ([H1]): iPhone announced January 2007. Release date conflict: June 29 vs July.\n"
                    "Second-hop passages ([H2]):\n"
                    "[1] Apple press release | iPhone available June 29, 2007\n"
                    "[2] TechCrunch 2007 | Launch event June 29\n"
                    "New facts ([H2]): Both sources confirm June 29 release\n"
                    "Conflict resolution: Press release (high proximity/expertise) and contemporaneous report override biography (lower proximity). June 29 resolution confirmed.\n"
                    "Comprehensive summary: iPhone announced January 2007 and released June 29, 2007. Claim verified."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Classify evidence gap and generate precise third-hop query",
                "stage_action": (
                    "1. Classify the gap as factual, contextual, or temporal.\n"
                    "2. Generate a query using 3-5 highly specific terms targeting ONLY the missing evidence.\n"
                    "IMPORTANT: Output ONLY the search query with no additional text - extra text breaks retrieval."
                ),
                "reasoning_questions": "What gap type prevents verification? Why is it critical? How many specific terms are needed?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Einstein won Nobel for relativity\n"
                    "Current evidence: Won 1921 Nobel for photoelectric effect, not relativity\n"
                    "Gap type: factual (official citation text)\n"
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
