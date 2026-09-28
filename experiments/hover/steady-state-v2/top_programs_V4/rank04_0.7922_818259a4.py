def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by gathering evidence through multiple hops of retrieval. Always be precise and avoid making assumptions. Focus on extracting and synthesizing factual evidence from retrieved passages.",
        "steps": [
            # Step 1: First-hop retrieval (k=10)
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
            # Step 2: Summarize first-hop evidence (entity extraction)
            {
                "number": 2,
                "title": "Extract entities and foundational facts",
                "step_type": "llm",
                "aim": "Extract key entities and foundational facts from the first-hop retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify the main entities (people, organizations, locations) and foundational facts directly related to the claim. "
                    "List these entities and facts in a concise bullet-point format."
                ),
                "reasoning_questions": "What are the key entities mentioned in these passages? What foundational facts about these entities are presented?",
                "example_reasoning": (
                    "The claim involves [claim topic]. Passage [1] mentions entities: [Entity1], [Entity2]. Foundational facts: [Fact1 about Entity1], [Fact2 about Entity2]."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (broad)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing context and generate a broad search query for connecting entities.",
                "stage_action": (
                    "Based on the first-hop summary, determine what additional context or connecting entities are needed "
                    "to link the claim to known facts. Write a concise, broad search query that will retrieve passages "
                    "about these entities or context.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What entities or concepts are missing to connect the first-hop evidence to the claim?",
                "example_reasoning": "The claim involves [X] but first-hop shows [Y]. Need information about [Z] that connects them. Query: \"Z concept and relationship to X and Y\"",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (k=10)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence (relationship identification)
            {
                "number": 5,
                "title": "Identify entity relationships",
                "step_type": "llm",
                "aim": "Identify relationships between entities from first-hop and the claim using second-hop evidence.",
                "stage_action": (
                    "Read all second-hop retrieved passages and identify how the entities from the first-hop relate to the claim. "
                    "Focus on causal, temporal, or associative relationships. Summarize these relationships in a concise list."
                ),
                "reasoning_questions": "How do the entities from the first-hop interact with each other or with the claim? What relationships (e.g., cause-effect, part-whole) are described?",
                "example_reasoning": (
                    "Passage [3] explains that [EntityA] (from first-hop) caused [Event] which is central to the claim. "
                    "This establishes a cause-effect relationship between EntityA and the claim."
                ),
                "dependencies": [4],
            },
            # Step 6: Gap check and generate third-hop query
            {
                "number": 6,
                "title": "Check evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient after two hops; generate specific query if gap exists.",
                "stage_action": (
                    "Review first-hop and second-hop evidence summaries. If the claim is 100% verified with direct evidence (with no gaps or ambiguities), "
                    "output an empty string. Otherwise, identify the precise missing evidence and write a very specific search query to find it.\n"
                    "Provide ONLY the search query or an empty string, no additional text."
                ),
                "reasoning_questions": "What specific fact is still missing to verify the claim with 100% certainty?",
                "example_reasoning": (
                    "Case 1 (sufficient): The claim states [claim]. First-hop shows [fact1], second-hop shows [fact2] which together directly confirm the claim with no gaps. Output: (empty string)\n"
                    "Case 2 (insufficient): Current evidence shows [A] and [B] but lacks verification of [C]. Query: \"[C] verified by [source] in [year]\""
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (k=10)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence (gap verification)
            {
                "number": 8,
                "title": "Verify evidence gap",
                "step_type": "llm",
                "aim": "Verify if the third-hop evidence fills the specific gap identified in the query generation step.",
                "stage_action": (
                    "Read all third-hop retrieved passages and check if they contain the precise fact that was missing (as described in the query). "
                    "If found, state the fact and how it fills the gap. If not found, note the absence."
                ),
                "reasoning_questions": "Does this passage directly provide the missing fact? How does it connect to the gap identified in step 6?",
                "example_reasoning": (
                    "The gap identified in step 6 was [missing fact]. Passage [5] states: '[exact quote]'. "
                    "This directly provides the missing fact and confirms [claim aspect]."
                ),
                "dependencies": [7],
            },
            # Step 9: Gap check and generate fourth-hop query
            {
                "number": 9,
                "title": "Check final evidence and generate fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient after three hops; generate ultra-specific query if gap remains.",
                "stage_action": (
                    "Review all evidence summaries (first, second, third hops). If the claim is 100% verified with direct evidence (with no gaps or ambiguities), "
                    "output an empty string. Otherwise, identify the exact missing verification point and write an extremely specific search query.\n"
                    "Provide ONLY the search query or an empty string, no additional text."
                ),
                "reasoning_questions": "What is the final missing verification point that would 100% confirm or refute the claim?",
                "example_reasoning": (
                    "Case 1 (sufficient): All evidence from hops 1-3 provides direct quotes confirming every aspect of the claim with no ambiguities. Output: (empty string)\n"
                    "Case 2 (insufficient): All evidence confirms [A], [B], [C] but lacks official verification of [D]. Query: \"[Official body] statement on [D] dated [year]\""
                ),
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (k=10)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }