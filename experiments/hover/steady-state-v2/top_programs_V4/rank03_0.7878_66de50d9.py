def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to gather all evidence needed to verify the claim by performing multi-hop retrieval. Always aim for complete coverage of supporting documents.",
        "steps": [
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
            {
                "number": 2,
                "title": "Process first-hop evidence",
                "step_type": "llm",
                "aim": "Integrate new evidence with prior evidence (if any), verify sufficiency, and generate next query if needed.",
                "stage_action": (
                    "You are given:\n"
                    "  - For the first hop: only the retrieved passages for the first hop.\n"
                    "  - For subsequent hops: \n"
                    "       * the integrated evidence summary from the previous process step (labeled 'EVIDENCE:')\n"
                    "       * the retrieved passages for the current hop.\n"
                    "Extract key facts from the current hop's passages. Integrate these facts with the prior evidence (if available) to form a new integrated evidence summary. "
                    "Check if the combined evidence is sufficient to verify the claim. If sufficient, output 'NO_QUERY' for the next query. Otherwise, generate a concise search query for the next hop that uses broad terms to maximize recall. "
                    "Output EXACTLY two lines:\n"
                    "  QUERY: <your query or NO_QUERY>\n"
                    "  EVIDENCE: <integrated evidence summary>\n"
                    "Do not output anything else."
                ),
                "reasoning_questions": (
                    "What specific fact is needed to verify the claim?\n"
                    "Does the current evidence provide that fact?\n"
                    "If not, what broad search terms would help find the missing fact?"
                ),
                "example_reasoning": (
                    "Example for first hop:\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  Retrieved passages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: Eiffel Tower completion date\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887.\n\n"
                    "Example for second hop:\n"
                    "  Prior evidence: The Eiffel Tower construction began in 1887.\n"
                    "  Retrieved passages: [1] Eiffel Tower completion | The tower was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: NO_QUERY\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887 and was completed in 1889."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Process second-hop evidence",
                "step_type": "llm",
                "aim": "Integrate new evidence with prior evidence (if any), verify sufficiency, and generate next query if needed.",
                "stage_action": (
                    "You are given:\n"
                    "  - For the first hop: only the retrieved passages for the first hop.\n"
                    "  - For subsequent hops: \n"
                    "       * the integrated evidence summary from the previous process step (labeled 'EVIDENCE:')\n"
                    "       * the retrieved passages for the current hop.\n"
                    "Extract key facts from the current hop's passages. Integrate these facts with the prior evidence (if available) to form a new integrated evidence summary. "
                    "Check if the combined evidence is sufficient to verify the claim. If sufficient, output 'NO_QUERY' for the next query. Otherwise, generate a concise search query for the next hop that uses broad terms to maximize recall. "
                    "Output EXACTLY two lines:\n"
                    "  QUERY: <your query or NO_QUERY>\n"
                    "  EVIDENCE: <integrated evidence summary>\n"
                    "Do not output anything else."
                ),
                "reasoning_questions": (
                    "What specific fact is needed to verify the claim?\n"
                    "Does the current evidence provide that fact?\n"
                    "If not, what broad search terms would help find the missing fact?"
                ),
                "example_reasoning": (
                    "Example for first hop:\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  Retrieved passages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: Eiffel Tower completion date\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887.\n\n"
                    "Example for second hop:\n"
                    "  Prior evidence: The Eiffel Tower construction began in 1887.\n"
                    "  Retrieved passages: [1] Eiffel Tower completion | The tower was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: NO_QUERY\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887 and was completed in 1889."
                ),
                "dependencies": [2, 3],
            },
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Process third-hop evidence",
                "step_type": "llm",
                "aim": "Integrate new evidence with prior evidence (if any), verify sufficiency, and generate next query if needed.",
                "stage_action": (
                    "You are given:\n"
                    "  - For the first hop: only the retrieved passages for the first hop.\n"
                    "  - For subsequent hops: \n"
                    "       * the integrated evidence summary from the previous process step (labeled 'EVIDENCE:')\n"
                    "       * the retrieved passages for the current hop.\n"
                    "Extract key facts from the current hop's passages. Integrate these facts with the prior evidence (if available) to form a new integrated evidence summary. "
                    "Check if the combined evidence is sufficient to verify the claim. If sufficient, output 'NO_QUERY' for the next query. Otherwise, generate a concise search query for the next hop that uses broad terms to maximize recall. "
                    "Output EXACTLY two lines:\n"
                    "  QUERY: <your query or NO_QUERY>\n"
                    "  EVIDENCE: <integrated evidence summary>\n"
                    "Do not output anything else."
                ),
                "reasoning_questions": (
                    "What specific fact is needed to verify the claim?\n"
                    "Does the current evidence provide that fact?\n"
                    "If not, what broad search terms would help find the missing fact?"
                ),
                "example_reasoning": (
                    "Example for first hop:\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  Retrieved passages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: Eiffel Tower completion date\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887.\n\n"
                    "Example for second hop:\n"
                    "  Prior evidence: The Eiffel Tower construction began in 1887.\n"
                    "  Retrieved passages: [1] Eiffel Tower completion | The tower was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: NO_QUERY\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887 and was completed in 1889."
                ),
                "dependencies": [4, 5],
            },
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Process fourth-hop evidence",
                "step_type": "llm",
                "aim": "Integrate new evidence with prior evidence (if any), verify sufficiency, and generate next query if needed.",
                "stage_action": (
                    "You are given:\n"
                    "  - For the first hop: only the retrieved passages for the first hop.\n"
                    "  - For subsequent hops: \n"
                    "       * the integrated evidence summary from the previous process step (labeled 'EVIDENCE:')\n"
                    "       * the retrieved passages for the current hop.\n"
                    "Extract key facts from the current hop's passages. Integrate these facts with the prior evidence (if available) to form a new integrated evidence summary. "
                    "Check if the combined evidence is sufficient to verify the claim. If sufficient, output 'NO_QUERY' for the next query. Otherwise, generate a concise search query for the next hop that uses broad terms to maximize recall. "
                    "Output EXACTLY two lines:\n"
                    "  QUERY: <your query or NO_QUERY>\n"
                    "  EVIDENCE: <integrated evidence summary>\n"
                    "Do not output anything else."
                ),
                "reasoning_questions": (
                    "What specific fact is needed to verify the claim?\n"
                    "Does the current evidence provide that fact?\n"
                    "If not, what broad search terms would help find the missing fact?"
                ),
                "example_reasoning": (
                    "Example for first hop:\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  Retrieved passages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: Eiffel Tower completion date\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887.\n\n"
                    "Example for second hop:\n"
                    "  Prior evidence: The Eiffel Tower construction began in 1887.\n"
                    "  Retrieved passages: [1] Eiffel Tower completion | The tower was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: NO_QUERY\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887 and was completed in 1889."
                ),
                "dependencies": [6, 7],
            },
            {
                "number": 9,
                "title": "Retrieve fifth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Process fifth-hop evidence",
                "step_type": "llm",
                "aim": "Integrate new evidence with prior evidence (if any), verify sufficiency, and generate next query if needed.",
                "stage_action": (
                    "You are given:\n"
                    "  - For the first hop: only the retrieved passages for the first hop.\n"
                    "  - For subsequent hops: \n"
                    "       * the integrated evidence summary from the previous process step (labeled 'EVIDENCE:')\n"
                    "       * the retrieved passages for the current hop.\n"
                    "Extract key facts from the current hop's passages. Integrate these facts with the prior evidence (if available) to form a new integrated evidence summary. "
                    "Check if the combined evidence is sufficient to verify the claim. If sufficient, output 'NO_QUERY' for the next query. Otherwise, generate a concise search query for the next hop that uses broad terms to maximize recall. "
                    "Output EXACTLY two lines:\n"
                    "  QUERY: <your query or NO_QUERY>\n"
                    "  EVIDENCE: <integrated evidence summary>\n"
                    "Do not output anything else."
                ),
                "reasoning_questions": (
                    "What specific fact is needed to verify the claim?\n"
                    "Does the current evidence provide that fact?\n"
                    "If not, what broad search terms would help find the missing fact?"
                ),
                "example_reasoning": (
                    "Example for first hop:\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  Retrieved passages: [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: Eiffel Tower completion date\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887.\n\n"
                    "Example for second hop:\n"
                    "  Prior evidence: The Eiffel Tower construction began in 1887.\n"
                    "  Retrieved passages: [1] Eiffel Tower completion | The tower was completed in 1889.\n"
                    "  Process step output:\n"
                    "    QUERY: NO_QUERY\n"
                    "    EVIDENCE: The Eiffel Tower construction began in 1887 and was completed in 1889."
                ),
                "dependencies": [8, 9],
            },
        ],
    }