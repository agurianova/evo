def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checking assistant. Your primary goal is to maximize retrieval coverage of supporting evidence by generating precise, entity-focused search queries. Always analyze evidence gaps methodically and prioritize missing verification elements.",
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
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify key entities and evidence gaps to generate precise second-hop query",
                "stage_action": "Analyze all retrieved passages to identify key entities and missing verification elements. Generate ONLY a concise search query targeting the most critical missing evidence.",
                "reasoning_questions": "What are the primary entities (people, organizations, events) in the claim?\nWhich specific claim elements lack supporting evidence in the passages?\nHow can we phrase a query using precise terminology to target the missing evidence?",
                "example_reasoning": "Claim: 'Marie Curie won two Nobel Prizes in Chemistry.'\nPassages: [1] Marie Curie | She was the first woman to win a Nobel Prize...\n[2] Nobel Prize | Awarded annually in six categories...\nGaps: Mentions first woman winner and Nobel categories but doesn't specify her two Chemistry prizes.\nQuery: 'Marie Curie Nobel Prize Chemistry count'",
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Second-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining evidence gaps after two hops",
                "stage_action": "Synthesize evidence from all prior passages. Identify the single most critical missing verification element. Generate ONLY a concise search query targeting this gap.",
                "reasoning_questions": "What new evidence did the second hop provide?\nWhich claim element remains unverified despite combined evidence?\nHow can we construct a query using domain-specific terminology to resolve this?",
                "example_reasoning": "After two hops: Confirmed Marie Curie won first Nobel (Physics 1903) but Chemistry prizes unclear.\nGaps: Need confirmation of second Chemistry prize year.\nQuery: 'Marie Curie second Nobel Prize Chemistry year'",
                "dependencies": [1, 3],
            },
            {
                "number": 5,
                "title": "Third-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final verification gaps after three hops",
                "stage_action": "Integrate all evidence to pinpoint the last missing verification element. Generate ONLY a concise search query targeting this specific gap.",
                "reasoning_questions": "What evidence has been gathered across all hops?\nWhich precise claim element remains unverified?\nHow can we phrase a query using technical terms to resolve this final gap?",
                "example_reasoning": "After three hops: Confirmed two Nobel Prizes (Physics 1903, Chemistry 1911) but claim states 'two in Chemistry'.\nGaps: Need clarification that second prize was Chemistry.\nQuery: 'Marie Curie 1911 Nobel Prize category'",
                "dependencies": [1, 3, 5],
            },
            {
                "number": 7,
                "title": "Fourth-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }