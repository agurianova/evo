#!/usr/bin/env python3
"""Cache facebook/esm2_t6_8M_UR50D for ImmRep25 mhca / peptide / tcra / tcrb.

Writes pmhctcr_data/esm2_t6_8M_UR50D/{by_id,pooled.npz,index.parquet,meta.json}.
The compiler reads this cache when encoders.sequence.arch is protein_lm.
CPU by default so a GPU evolution run can keep the H100.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from problems.pmhctcr.assets import ESM2_HIDDEN, ESM2_MODEL_ID, ESM2_RELDIR
from problems.pmhctcr.dataset import data_root

_KIND_PREFIX = {
    "mhca": "mhc",
    "epi": "peptide",
    "tcra": "tcra",
    "tcrb": "tcrb",
}


def _kind(entity_id: str) -> str | None:
    prefix = entity_id.split("_", 1)[0]
    return _KIND_PREFIX.get(prefix)


def _targets(seqs: dict[str, str]) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for entity_id, seq in seqs.items():
        kind = _kind(entity_id)
        if kind is None or not seq:
            continue
        out.append((entity_id, kind, str(seq)))
    out.sort(key=lambda row: (len(row[2]), row[0]))
    return out


def _encode_batch(model, tokenizer, seqs: list[str], device: torch.device) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    enc = tokenizer(
        seqs,
        padding=True,
        truncation=True,
        return_tensors="pt",
        return_special_tokens_mask=True,
    )
    special = enc.pop("special_tokens_mask")
    enc = {k: v.to(device) for k, v in enc.items()}
    special = special.to(device)
    with torch.inference_mode():
        hidden = model(**enc).last_hidden_state
    residue_mask = enc["attention_mask"].bool() & ~special.bool()
    rows: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for i, seq in enumerate(seqs):
        res = hidden[i, residue_mask[i]].detach().float().cpu().numpy()
        if res.shape[0] != len(seq):
            raise RuntimeError(
                f"ESM residue length {res.shape[0]} != sequence length {len(seq)}"
            )
        pooled = res.mean(axis=0).astype(np.float32)
        cls = hidden[i, 0].detach().float().cpu().numpy().astype(np.float32)
        rows.append((res.astype(np.float16), pooled, cls))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--cuda", action="store_true", help="Use GPU (off by default).")
    parser.add_argument("--model", default=ESM2_MODEL_ID)
    args = parser.parse_args()

    root = args.data_root or data_root()
    seq_path = root / "sequences.json"
    seqs = json.loads(seq_path.read_text())
    jobs = _targets(seqs)
    out_dir = root / ESM2_RELDIR
    by_id = out_dir / "by_id"
    by_id.mkdir(parents=True, exist_ok=True)

    pending = [(eid, kind, seq) for eid, kind, seq in jobs if not (by_id / f"{eid}.npz").is_file()]
    print(f"esm2 cache: {len(jobs)} sequences, {len(pending)} to encode, dir={out_dir}")

    if pending:
        from transformers import AutoTokenizer, EsmModel

        device = torch.device("cuda" if args.cuda and torch.cuda.is_available() else "cpu")
        print(f"esm2 cache: loading {args.model} on {device}")
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        model = EsmModel.from_pretrained(args.model, add_pooling_layer=False)
        model.to(device)
        model.eval()
        bs = max(1, args.batch_size)
        for start in range(0, len(pending), bs):
            chunk = pending[start : start + bs]
            encoded = _encode_batch(model, tokenizer, [row[2] for row in chunk], device)
            for (entity_id, kind, seq), (residue, pooled, cls) in zip(chunk, encoded):
                np.savez_compressed(
                    by_id / f"{entity_id}.npz",
                    residue=residue,
                    pooled=pooled,
                    cls=cls,
                    n_aa=np.int32(len(seq)),
                    dim=np.int32(ESM2_HIDDEN),
                    kind=np.asarray(kind),
                    entity_id=np.asarray(entity_id),
                    sha256=np.asarray(hashlib.sha256(seq.encode()).hexdigest()),
                )
            done = min(start + bs, len(pending))
            if done == len(pending) or done % 50 < bs or start == 0:
                print(f"esm2 cache: encoded {done}/{len(pending)}", flush=True)
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    index_rows = []
    pooled: dict[str, np.ndarray] = {}
    for entity_id, kind, seq in jobs:
        path = by_id / f"{entity_id}.npz"
        with np.load(path, allow_pickle=False) as z:
            vec = np.asarray(z["pooled"], dtype=np.float32)
            n_aa = int(z["n_aa"])
        if vec.shape[0] != ESM2_HIDDEN or n_aa != len(seq):
            raise RuntimeError(f"corrupt cache file {path}")
        pooled[entity_id] = vec
        index_rows.append(
            {
                "entity_id": entity_id,
                "kind": kind,
                "n_aa": len(seq),
                "sha256": hashlib.sha256(seq.encode()).hexdigest(),
                "path": f"by_id/{entity_id}.npz",
            }
        )
    np.savez_compressed(out_dir / "pooled.npz", **pooled)
    pd.DataFrame(index_rows).to_parquet(out_dir / "index.parquet", index=False)
    meta = {
        "model": args.model,
        "hidden_dim": ESM2_HIDDEN,
        "repr": "last_hidden_state",
        "pooling": "mean over residue tokens (no cls/eos/pad)",
        "dtype_residue": "float16",
        "dtype_pooled": "float32",
        "kinds": sorted({k for _, k, _ in jobs}),
        "n_sequences": len(jobs),
        "device": "cuda" if args.cuda else "cpu",
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"esm2 cache: wrote {len(jobs)} ids -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
