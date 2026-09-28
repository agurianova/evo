"""Ablation: evaluate best V3 chain from dynamic-topology with retrieve replaced by retrieve_deep.

Original: 67.67% discrete coverage (5 repeats, mean) with retrieve_deep (k=10)
This: same chain but all retrieve_deep → retrieve (k=7)
"""

from pathlib import Path
from statistics import mean, stdev
import sys

PROJ = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJ))

from problems.chains.chain_runner import run_chain_on_dataset  # noqa: E402
from problems.chains.chain_validation import validate_chain_spec  # noqa: E402
from problems.chains.client import LLMClient  # noqa: E402
from problems.chains.hover.full_no_deep.config import FULL_CHAIN_CONFIG  # noqa: E402
from problems.chains.hover.full_no_deep.test import (  # noqa: E402
    evaluate_discrete_coverage_adaptive,
    load_test_context,
)
from problems.chains.hover.shared_config import (  # noqa: E402
    get_llm_config,
    outer_context_builder,
)
from problems.chains.hover.utils.retrieval import make_retrieve_fn  # noqa: E402


def entrypoint():
    """Best V3 chain with retrieve_deep replaced by retrieve."""
    return {
        "system_prompt": "You are a fact-checker verifying claims by retrieving evidence step-by-step. After each hop, first summarize the key facts from the retrieved passages, then identify the next specific missing fact with resolved entity ambiguities, and finally generate a precise search query for that missing fact. Focus on the critical gap to maximize retrieval coverage.",
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
            },
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Summarize first-hop evidence, identify the missing fact with entity disambiguation, and generate a precise second-hop query.",
                "stage_action": (
                    "Read the first-hop passages. First, write a one-sentence summary of the key facts. "
                    "Then, identify what specific fact is still missing to verify the claim, resolving any entity ambiguities (e.g., 'Paris' refers to the city in France). "
                    "Finally, write a concise search query to find that missing fact. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the concise summary of the first-hop evidence? "
                    "What specific fact is missing? "
                    "Which entities or relationships need verification and what are their resolved forms? "
                    "What is the most precise query for the missing fact?"
                ),
                "example_reasoning": "First-hop passages confirm that Marie Curie discovered radium. The claim also states she won two Nobel Prizes, which is not confirmed. The entity 'Nobel Prize' refers to the award in Physics and Chemistry. Missing fact: the years she won the Nobel Prizes. Query: 'Marie Curie Nobel Prize years'",
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
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Summarize evidence from first and second hops, identify the missing fact with entity disambiguation, and generate a precise third-hop query.",
                "stage_action": (
                    "Read the first-hop passages (from step1) and second-hop passages (from step3). "
                    "First, write a one-sentence summary of the key facts from both. "
                    "Then, identify what specific fact is still missing to verify the claim, resolving any entity ambiguities. "
                    "Finally, write a concise search query for the missing evidence. "
                    "Provide ONLY the query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the concise summary of the evidence so far? "
                    "What new evidence did the second hop provide? "
                    "What specific fact remains missing? "
                    "Which entities or relationships are ambiguous and how are they resolved? "
                    "What is the most precise query for the missing fact?"
                ),
                "example_reasoning": "First-hop confirmed Marie Curie discovered radium, second-hop confirmed she won Nobel Prizes in 1903 and 1911. The claim states she was the first woman to win, which is not confirmed. The entity 'first woman' refers to Nobel Prize winners. Missing fact: previous female Nobel laureates. Query: 'first woman Nobel Prize winner before Marie Curie'",
                "dependencies": [1, 3],
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
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Summarize evidence from all hops, identify the final missing fact with entity disambiguation, and generate a precise fourth-hop query.",
                "stage_action": (
                    "Read the first-hop (step1), second-hop (step3), and third-hop (step5) passages. "
                    "First, write a one-sentence summary of the key facts. "
                    "Then, identify the single most critical missing fact to verify the claim, resolving any entity ambiguities. "
                    "Finally, write a concise search query for that fact. "
                    "Provide ONLY the query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the concise summary of all evidence? "
                    "What specific fact is still missing? "
                    "Which entity or relationship is unconfirmed and how is it resolved? "
                    "What is the most precise query for the missing fact?"
                ),
                "example_reasoning": "First-hop: radium discovery, second-hop: Nobel Prizes in 1903/1911, third-hop: no prior female winners. The claim states she was the first woman, which is confirmed. However, the entity 'woman' refers to female scientists and the relationship 'first' is verified. No critical missing fact. Query: 'Marie Curie first woman Nobel Prize'",
                "dependencies": [1, 3, 5],
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
        ],
    }


if __name__ == "__main__":
    n_repeats = 5
    chain_spec = entrypoint()

    chain = validate_chain_spec(
        chain_spec,
        mode="full_chain",
        full_chain_config=FULL_CHAIN_CONFIG,
    )

    context = load_test_context()
    dataset = context["test_dataset"]

    client = LLMClient(**get_llm_config())
    tool_registry = {
        "retrieve": make_retrieve_fn(
            context["bm25s_index_dir"], k=7, corpus_path=context["corpus_path"]
        ),
    }

    print(
        "Evaluating best V3 chain with retrieve (k=7) instead of retrieve_deep (k=10)"
    )
    print("Original V3 result: 67.67% discrete coverage (5 repeats)")
    print(f"Test samples: {len(dataset)}")
    print(f"Repeats: {n_repeats}\n")

    coverages = []
    for rep in range(1, n_repeats + 1):
        results = run_chain_on_dataset(
            chain, client, dataset, outer_context_builder, tool_registry
        )
        discrete_scores = evaluate_discrete_coverage_adaptive(dataset, results, chain)
        coverage = mean(discrete_scores) if discrete_scores else 0.0
        coverages.append(coverage)
        print(f"  Repeat {rep}/{n_repeats}: discrete coverage = {coverage:.4f}")

    print("\n=== Ablation Results ===")
    mean_cov = mean(coverages)
    std_cov = stdev(coverages) if len(coverages) > 1 else 0.0
    print(f"Discrete Coverage (mean): {mean_cov:.4f}")
    print(f"Discrete Coverage (std):  {std_cov:.4f}")
    print(f"Discrete Coverage (all):  {[f'{c:.4f}' for c in coverages]}")
    print("\nOriginal (retrieve_deep k=10): 67.67% ± 0.78pp")
    print(
        f"Ablation (retrieve k=7):       {mean_cov * 100:.2f}% ± {std_cov * 100:.2f}pp"
    )
    print(f"Delta:                         {(mean_cov - 0.6767) * 100:+.2f}pp")
