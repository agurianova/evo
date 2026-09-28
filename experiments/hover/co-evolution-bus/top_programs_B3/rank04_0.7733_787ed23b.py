def entrypoint():
    return {
        "system_prompt": "Fact-checker. Query steps (3,6): ONLY bare search query. Rules: 1) Specific entities/dates 2) Step3: 5-8 words; Step6: 5-10 words 3) Disambiguate entities. Prioritize credible sources.",
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
                "aim": "Extract claim-relevant entities, dates, and relationships from first-hop passages for query generation.",
                "stage_action": (
                    "1. For each passage, extract entities, dates, and relationships relevant to the claim. Note source article title.\n"
                    "2. Identify conflicts and note source credibility (primary > secondary).\n"
                    "3. Do not resolve conflicts; step5 will resolve.\n"
                    "4. Output:\n"
                    "   - Key facts (with source titles)\n"
                    "   - Remaining gaps: [list each gap as 'Remaining gap: ...']"
                ),
                "reasoning_questions": "What specific entities, dates, relationships are present? What sources are most credible? What gaps remain for verification? How can gaps be phrased for search?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Marie Curie was born in Paris.\n"
                    "Retrieved passages:\n"
                    "[0] Marie Curie | Born Maria Salomea Skłodowska in Warsaw, Poland, on 7 November 1867...\n"
                    "[1] Paris | ...birthplace of Marie Curie...\n"
                    "Key facts: \n"
                    "- Marie Curie born in Warsaw, Poland, on 7 November 1867 (source: Marie Curie)\n"
                    "- Paris claimed as birthplace (source: Paris)\n"
                    "Conflict: Two sources give different birthplaces (Warsaw vs Paris). Source 'Marie Curie' is primary.\n"
                    "Remaining gap: Remaining gap: Marie Curie birthplace confirmation"
                ),
                "dependencies": [1],
                "frozen": False,
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate a precise second-hop search query from identified gaps.",
                "stage_action": (
                    "Based on the 'Remaining gap:' statements, generate a search query that:\n"
                    "- Is 5-8 words\n"
                    "- Uses specific entities and dates\n"
                    "- Includes 1-2 synonyms from first-hop passages\n"
                    "- Uses domain-specific terminology\n"
                    "- Disambiguates ambiguous entities (e.g., 'entity (domain context)')\n"
                    "Output ONLY the search query."
                ),
                "reasoning_questions": "What gap is critical? What synonyms/domain terms can improve recall? How to disambiguate? How to fit 5-8 words?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: The first iPhone was released in 2007.\n"
                    "First-hop summary:\n"
                    "Key facts: \n"
                    "- iPhone introduced by Steve Jobs in January 2007 (source: iPhone)\n"
                    "- Became available to public in June 2007 (source: Apple Inc.)\n"
                    "Remaining gap: Remaining gap: exact public release date (day of month)\n"
                    "Synonyms: 'launch date', 'availability date'\n"
                    "Domain terms: 'Apple', 'iOS'\n"
                    "Disambiguation: 'iPhone 2007 public release date' (to avoid confusion with announcement)\n"
                    "Query: first iPhone public release date Apple June 2007"
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
                "aim": "Integrate first and second hop evidence with conflict resolution for gap identification.",
                "stage_action": (
                    "1. Extract entities, dates, relationships from second-hop passages; note source titles.\n"
                    "2. Integrate with first-hop summary, preserving source information.\n"
                    "3. Resolve conflicts using: official documents > academic papers > news > general sources. Explain resolution.\n"
                    "4. Identify remaining gaps: list each as 'Remaining gap: ...'"
                ),
                "reasoning_questions": "What new facts? How do they relate to first-hop? How to resolve conflicts using source hierarchy? What gaps remain?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Marie Curie died in 1934.\n"
                    "First-hop summary:\n"
                    "Key facts: \n"
                    "- Marie Curie died on July 4, 1934 from aplastic anemia (source: Marie Curie)\n"
                    "- Some sources cite different dates (source: Radioactivity)\n"
                    "Remaining gap: Remaining gap: exact death date confirmation\n"
                    "Second-hop passages:\n"
                    "[0] Marie Curie | Died July 4, 1934 in Passy, France from aplastic anemia.\n"
                    "[1] Radioactivity | ...Curie's death in 1935 due to radiation exposure...\n"
                    "New facts: \n"
                    "- Passage 0 (source: Marie Curie) confirms death on July 4, 1934.\n"
                    "- Passage 1 (source: Radioactivity) states 1935.\n"
                    "Conflict resolution: Source 'Marie Curie' (primary biography) > 'Radioactivity' (general topic), so death date is July 4, 1934.\n"
                    "Remaining gaps: None - death date fully verified.\n"
                    "Comprehensive summary: Marie Curie died on July 4, 1934 in Passy, France from aplastic anemia, as confirmed by authoritative biographical sources."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate a precise third-hop search query targeting the most distant evidence.",
                "stage_action": (
                    "Based on the 'Remaining gap:' statements, generate a search query that:\n"
                    "- Is 5-10 words\n"
                    "- Uses specific entities and dates\n"
                    "- Includes 1-2 synonyms from first-hop passages\n"
                    "- Uses domain-specific terminology\n"
                    "- Disambiguates ambiguous entities using 'entity (domain context)' format\n"
                    "Output ONLY the search query."
                ),
                "reasoning_questions": "What specific gap remains? How to expand with synonyms/domain terms? How to disambiguate entities? How to fit 5-10 words?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: Albert Einstein won the Nobel Prize for his theory of relativity.\n"
                    "Current evidence summary:\n"
                    "Key facts: \n"
                    "- Einstein won Nobel Prize in 1921 (source: Albert Einstein)\n"
                    "- Specifically for photoelectric effect, not relativity (source: Nobel Prize)\n"
                    "Remaining gaps: Remaining gap: exact wording of Nobel Prize citation\n"
                    "Synonyms: 'official citation', 'award motivation'\n"
                    "Domain terms: 'nobelprize.org', 'Nobel Assembly'\n"
                    "Disambiguation: 'Einstein Nobel Prize citation (physics)'\n"
                    "Query: Einstein Nobel Prize official citation photoelectric effect nobelprize.org"
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
