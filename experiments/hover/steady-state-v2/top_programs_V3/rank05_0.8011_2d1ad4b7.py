def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier specializing in multi-hop claim verification. Your goal is to maximize the retrieval of supporting documents by generating precise search queries at each hop. Always prioritize recall to ensure no relevant evidence is missed. When generating search queries, focus on the specific missing information and use precise terminology from the evidence summary.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve first-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant to verifying the claim. "
                    "Summarize the most important evidence found in a concise manner."
                ),
                "reasoning_questions": "What are the main entities and events mentioned in the passages? How do they relate to the claim?",
                "example_reasoning": (
                    "The claim is about the cause of World War I. The passages mention the assassination of Archduke Franz Ferdinand. "
                    "This is a key event that triggered the war. Summary: The assassination of Archduke Franz Ferdinand by Gavrilo Princip in 1914 is widely regarded as the immediate cause of World War I."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary of the first-hop evidence, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific aspect of the claim is not yet supported by the first-hop evidence? What entities or events should the next search focus on?",
                "example_reasoning": (
                    "The first-hop evidence established the assassination as the trigger, but does not explain the underlying causes. "
                    "We need evidence about the alliance systems and militarism in Europe. Query: 'causes of World War I alliance systems militarism'"
                ),
                "dependencies": [2],
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
            },
            {
                "number": 5,
                "title": "Integrate first and second hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the raw passages from the first hop (step1) and the raw passages from the second hop (step4). "
                    "Produce a unified evidence summary covering all relevant facts found so far."
                ),
                "reasoning_questions": "How do the facts from the second hop connect to the first hop? Are there any contradictions or reinforcements between the two sets of evidence?",
                "example_reasoning": (
                    "First hop: The assassination of Archduke Franz Ferdinand. Second hop: The complex system of alliances (Triple Entente and Triple Alliance) meant that a conflict between two countries could draw in multiple nations. "
                    "Integration: The assassination triggered a chain reaction due to pre-existing alliances, leading to the outbreak of World War I."
                ),
                "dependencies": [1, 4],
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the integrated evidence summary, determine what additional evidence is still needed to "
                    "fully verify the claim. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific gap remains after integrating the first two hops? What precise information would resolve this gap?",
                "example_reasoning": (
                    "We have the trigger and the alliance system, but we lack evidence of the actual mobilization orders and declarations of war. "
                    "Query: 'World War I mobilization declarations of war 1914'"
                ),
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Integrate all evidence (three hops)",
                "step_type": "llm",
                "aim": "Combine all retrieved evidence into a final comprehensive summary.",
                "stage_action": (
                    "Integrate the raw passages from the first hop (step1), second hop (step4), and third hop (step7). "
                    "Produce a single, coherent evidence summary covering all aspects of the claim."
                ),
                "reasoning_questions": "How do the facts from the third hop complete the picture? Is there now sufficient evidence to verify the claim, or are there still gaps?",
                "example_reasoning": (
                    "First hop: Assassination event. Second hop: Alliance systems. Third hop: Germany's 'blank check' to Austria and the subsequent mobilization. "
                    "Integration: The assassination led Austria-Hungary to issue an ultimatum to Serbia, supported by Germany's blank check. "
                    "Russia mobilized in support of Serbia, leading Germany to declare war on Russia and France, and invade Belgium, which brought Britain into the war."
                ),
                "dependencies": [1, 4, 7],
            },
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify any remaining gaps and generate a search query for the fourth hop.",
                "stage_action": (
                    "Based on the final integrated evidence summary, determine if there is still missing evidence to fully verify the claim. "
                    "If so, write a concise search query for the fourth hop. If all evidence is found, output 'All evidence found'.\n"
                    "Provide ONLY the query or the exact string 'All evidence found', no additional text."
                ),
                "reasoning_questions": "After reviewing all evidence, what specific piece of information is still missing? If nothing is missing, confirm completeness.",
                "example_reasoning": (
                    "We have the sequence of events but lack the exact text of the ultimatum. Query: 'Austro-Hungarian ultimatum to Serbia 1914 text'"
                ),
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }