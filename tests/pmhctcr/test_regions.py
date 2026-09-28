from __future__ import annotations

from problems.pmhctcr.dataset import load_folds
from problems.pmhctcr.genotype import default_genotype
from problems.pmhctcr.operators import apply_operator
from problems.pmhctcr.regions import (
    _GERMLINE_CDR,
    chain_region_from_row,
    split_chain,
    vj_onehot_from_row,
)


def test_cdr3_and_cdr1_are_substrings_of_full_chain():
    tcr = load_folds()["train"].iloc[0]
    parts = split_chain(
        str(tcr["tcra_seq"]), str(tcr["tcra_seq_cdr3"]), str(tcr["tcra_vgene"])
    )
    assert parts["cdr3"] == tcr["tcra_seq_cdr3"]
    assert parts["cdr3"] in parts["full"]
    assert parts["cdr1"]
    assert parts["cdr1"] in parts["full"]
    assert parts["fr1"]
    assert parts["fr4"]
    assert chain_region_from_row(tcr, "a", "cdr3") == tcr["tcra_seq_cdr3"]
    all_cdr = chain_region_from_row(tcr, "a", "all_cdr")
    assert tcr["tcra_seq_cdr3"] in all_cdr


def test_imgt_germline_loops_match_named_v_alleles():
    tcr = load_folds()["train"].drop_duplicates("tcr_id")
    row = tcr[tcr["tcra_vgene"] == "TRAV1-1*01"].iloc[0]
    parts = split_chain(
        str(row["tcra_seq"]), str(row["tcra_seq_cdr3"]), str(row["tcra_vgene"])
    )
    assert parts["cdr1"] == "TSGFYG"
    assert parts["cdr2"] == "NALDGL"
    assert "W" not in parts["cdr1"]
    assert parts["fr2"].startswith("LSWY")
    assert parts["cdr3"] == row["tcra_seq_cdr3"]
    assert len(parts["fr4"]) == 11
    from problems.pmhctcr.regions import region_indices

    idx = region_indices(
        str(row["tcra_seq"]),
        "cdr1",
        cdr3=str(row["tcra_seq_cdr3"]),
        vgene=str(row["tcra_vgene"]),
    )
    extracted = "".join(str(row["tcra_seq"])[i] for i in idx)
    assert extracted == "TSGFYG"
    for _, rec in tcr.iterrows():
        for chain, seq_c, cdr3_c, vg_c in (
            ("a", "tcra_seq", "tcra_seq_cdr3", "tcra_vgene"),
            ("b", "tcrb_seq", "tcrb_seq_cdr3", "tcrb_vgene"),
        ):
            germ = _GERMLINE_CDR[str(rec[vg_c])]
            sliced = split_chain(str(rec[seq_c]), str(rec[cdr3_c]), str(rec[vg_c]))
            assert sliced["cdr1"] == germ[0]
            assert sliced["cdr2"] == germ[1]
            assert sliced["cdr3"] == rec[cdr3_c]
            reconstructed = (
                sliced["fr1"]
                + sliced["cdr1"]
                + sliced["fr2"]
                + sliced["cdr2"]
                + sliced["fr3"]
                + sliced["cdr3"]
                + sliced["fr4"]
            )
            assert str(rec[seq_c]).startswith(reconstructed)
            from_row = chain_region_from_row(rec, chain, "cdr1")
            assert from_row == germ[0]
    motif = split_chain(str(row["tcra_seq"]), str(row["tcra_seq_cdr3"]))
    assert motif["cdr1"] == "TSGFYG"
    assert "W" not in motif["cdr1"]


def test_vgene_onehot_hits_named_allele():
    tcr = load_folds()["train"].iloc[0]
    vec = vj_onehot_from_row(tcr, alpha=True, beta=True)
    assert vec.sum() >= 2.0
    assert vec.max() == 1.0


def test_guided_sequence_sets_cdr1():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_SEQUENCE",
        guided_text="OPERATOR=CHANGE_SEQUENCE; set encoders.sequence.region to cdr1",
    )
    assert child.encoders.sequence.region == "cdr1"
