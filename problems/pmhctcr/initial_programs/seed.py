"""pMHC-TCR child generated from a JSON genotype. Do not hand-edit."""
from __future__ import annotations

# EVOLVE-BLOCK-START genotype
GENOTYPE_JSON = '{\n  "calibration": {\n    "temperature": 1.0\n  },\n  "encoders": {\n    "sequence": {\n      "arch": "transformer",\n      "hidden_dim": 256,\n      "pooling": "mean",\n      "pretrained": false,\n      "region": "full"\n    },\n    "structure": {\n      "arch": "gat",\n      "edges": {\n        "k": 16,\n        "radius_A": 8.0,\n        "type": "knn"\n      },\n      "hidden_dim": 256,\n      "pooling": "mean",\n      "scope": "full_complex"\n    },\n    "surface": {\n      "metrics": [\n        "cosine"\n      ],\n      "patch_boundary": "nn_radius",\n      "patch_radius_A": 12.0,\n      "spots": {\n        "derived": [],\n        "enabled": false,\n        "linkage_A": 2.0,\n        "metric": "l2",\n        "subsample": 256,\n        "threshold": 1.7\n      },\n      "threshold": 0.7,\n      "topk": 10\n    }\n  },\n  "inputs": {\n    "masif": {\n      "pmhc_flipped": false,\n      "tcr_direct": false\n    },\n    "pdb": {\n      "kind": null,\n      "present": false\n    },\n    "sequence": {\n      "mhc": true,\n      "peptide": true,\n      "tcr_alpha": true,\n      "tcr_beta": true\n    }\n  },\n  "interaction": {\n    "fusion": null,\n    "method": null,\n    "pairs": []\n  },\n  "meta": {\n    "generation": 0,\n    "operator_applied": null,\n    "parent_id": null\n  },\n  "model": {\n    "dropout": 0.1,\n    "ensemble_members": [],\n    "hidden_dim": 256,\n    "num_heads": 4,\n    "num_layers": 2,\n    "residual": true,\n    "type": "mlp_features"\n  },\n  "seed": 0,\n  "training": {\n    "augmentation": {\n      "seq_mask_p": 0.0,\n      "structure_edge_dropout_p": 0.0\n    },\n    "batch_size": 64,\n    "focal_gamma": 2.0,\n    "hard_negative_ratio": 0.3,\n    "loss": "bce",\n    "lr": 0.001,\n    "optimizer": "adamw",\n    "sampling": "random",\n    "scheduler": "none",\n    "weight_decay": 0.0001\n  }\n}\n'
# EVOLVE-BLOCK-END genotype

# insight: (unguided)
# head: torch
# SeqEncoder: bag_of_aa
# GAT: off
# cross_attn: off
# tabular: sequence; spots off
# model.type: mlp_features  layers=2  hid=256
# ignored: encoders.sequence.arch=transformer (bag-of-AA; no SeqEncoder until CHANGE_SEQUENCE cnn/transformer or CHANGE_MODEL seq_dual/seq_cross/multimodal)

def entrypoint():
    try:
        from problems.pmhctcr.compiler import compile_genotype
    except ImportError:
        from compiler import compile_genotype
    return compile_genotype(GENOTYPE_JSON)
