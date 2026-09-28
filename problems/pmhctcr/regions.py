"""TCR CDR/FR slices and V/J-gene features.

ImmRep25 tables have ``tcra/b_seq``, ``*_seq_cdr3``, and IMGT gene names, but
not CDR1/2/FR. ANARCI / tidytcells / Biopython are not installed here.

CDR3 is taken from the table (always a substring of the full chain). CDR1/2
are the ungapped IMGT germline loops for the named TRAV/TRBV allele, located
as substrings of the V-prefix (100% of ImmRep25 alleles). FR1/2/3 are the
flanking pieces; FR4 is the J suffix after CDR3 (IMGT 118–128, 11 aa).

If the allele is unknown or a loop is not found, fall back to Cys23 + Trp41
(WY[QKR]) anchors: FR1 through Cys+3, CDR1 until two residues before Trp,
FR2 = 17 aa, CDR2/FR3 split the remainder. Linear Cys23–Cys104 interpolation
is not used — it swallowed conserved Trp41 into CDR1.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

# Alleles observed in ImmRep25 ``tcr.parquet`` (stable one-hot axes).
TRAV_ALLELES = (
    "TRAV1-1*01",
    "TRAV1-2*01",
    "TRAV10*01",
    "TRAV12-1*01",
    "TRAV12-2*01",
    "TRAV12-3*01",
    "TRAV13-1*01",
    "TRAV13-2*01",
    "TRAV16*01",
    "TRAV17*01",
    "TRAV19*01",
    "TRAV2*01",
    "TRAV20*01",
    "TRAV21*01",
    "TRAV22*01",
    "TRAV23/DV6*01",
    "TRAV24*01",
    "TRAV25*01",
    "TRAV26-1*01",
    "TRAV26-2*01",
    "TRAV27*01",
    "TRAV29/DV5*01",
    "TRAV3*01",
    "TRAV30*01",
    "TRAV34*01",
    "TRAV35*01",
    "TRAV36/DV7*01",
    "TRAV38-1*01",
    "TRAV38-2/DV8*01",
    "TRAV39*01",
    "TRAV4*01",
    "TRAV5*01",
    "TRAV6*01",
    "TRAV8-1*01",
    "TRAV8-2*01",
    "TRAV8-3*01",
    "TRAV8-4*01",
    "TRAV8-6*01",
    "TRAV9-2*01",
)
TRBV_ALLELES = (
    "TRBV10-1*01",
    "TRBV10-2*01",
    "TRBV10-3*01",
    "TRBV11-1*01",
    "TRBV11-2*01",
    "TRBV11-3*01",
    "TRBV12-1*01",
    "TRBV12-5*01",
    "TRBV13*01",
    "TRBV14*01",
    "TRBV15*01",
    "TRBV16*01",
    "TRBV18*01",
    "TRBV19*01",
    "TRBV2*01",
    "TRBV20-1*01",
    "TRBV24-1*01",
    "TRBV25-1*01",
    "TRBV27*01",
    "TRBV28*01",
    "TRBV29-1*01",
    "TRBV3-1*01",
    "TRBV30*01",
    "TRBV4-1*01",
    "TRBV4-2*01",
    "TRBV4-3*01",
    "TRBV5-1*01",
    "TRBV5-4*01",
    "TRBV5-5*01",
    "TRBV5-6*01",
    "TRBV5-8*01",
    "TRBV6-1*01",
    "TRBV6-2*01",
    "TRBV6-4*01",
    "TRBV6-5*01",
    "TRBV6-6*01",
    "TRBV7-1*01",
    "TRBV7-2*01",
    "TRBV7-3*01",
    "TRBV7-6*01",
    "TRBV7-8*01",
    "TRBV7-9*01",
    "TRBV9*01",
)
TRAJ_ALLELES = (
    "TRAJ10*01",
    "TRAJ11*01",
    "TRAJ12*01",
    "TRAJ13*01",
    "TRAJ15*01",
    "TRAJ16*01",
    "TRAJ17*01",
    "TRAJ18*01",
    "TRAJ20*01",
    "TRAJ21*01",
    "TRAJ22*01",
    "TRAJ23*01",
    "TRAJ24*01",
    "TRAJ26*01",
    "TRAJ27*01",
    "TRAJ28*01",
    "TRAJ29*01",
    "TRAJ3*01",
    "TRAJ30*01",
    "TRAJ31*01",
    "TRAJ32*01",
    "TRAJ33*01",
    "TRAJ34*01",
    "TRAJ38*01",
    "TRAJ39*01",
    "TRAJ4*01",
    "TRAJ40*01",
    "TRAJ41*01",
    "TRAJ42*01",
    "TRAJ43*01",
    "TRAJ44*01",
    "TRAJ45*01",
    "TRAJ47*01",
    "TRAJ48*01",
    "TRAJ49*01",
    "TRAJ5*01",
    "TRAJ50*01",
    "TRAJ52*01",
    "TRAJ53*01",
    "TRAJ54*01",
    "TRAJ56*01",
    "TRAJ57*01",
    "TRAJ6*01",
    "TRAJ7*01",
    "TRAJ8*01",
    "TRAJ9*01",
)
TRBJ_ALLELES = (
    "TRBJ1-1*01",
    "TRBJ1-2*01",
    "TRBJ1-3*01",
    "TRBJ1-4*01",
    "TRBJ1-5*01",
    "TRBJ1-6*01",
    "TRBJ2-1*01",
    "TRBJ2-2*01",
    "TRBJ2-3*01",
    "TRBJ2-4*01",
    "TRBJ2-5*01",
    "TRBJ2-6*01",
    "TRBJ2-7*01",
)

_TRAV_INDEX = {n: i for i, n in enumerate(TRAV_ALLELES)}
_TRBV_INDEX = {n: i for i, n in enumerate(TRBV_ALLELES)}
_TRAJ_INDEX = {n: i for i, n in enumerate(TRAJ_ALLELES)}
_TRBJ_INDEX = {n: i for i, n in enumerate(TRBJ_ALLELES)}

# Ungapped IMGT CDR1 / CDR2 for ImmRep25 alleles (tcrdist3 human V reference).
_GERMLINE_CDR: dict[str, tuple[str, str]] = {
    "TRAV1-1*01": ("TSGFYG", "NALDGL"),
    "TRAV1-2*01": ("TSGFNG", "NVLDGL"),
    "TRAV10*01": ("VSPFSN", "MTFSENT"),
    "TRAV12-1*01": ("NSASQS", "VYSSGN"),
    "TRAV12-2*01": ("DRGSQS", "IYSNGD"),
    "TRAV12-3*01": ("NSAFQY", "TYSSGN"),
    "TRAV13-1*01": ("DSASNY", "IRSNVGE"),
    "TRAV13-2*01": ("NSASDY", "IRSNMDK"),
    "TRAV16*01": ("YSGSPE", "HISR"),
    "TRAV17*01": ("TSINN", "IRSNERE"),
    "TRAV19*01": ("TRDTTYY", "RNSFDEQN"),
    "TRAV2*01": ("VSNAYN", "GSKP"),
    "TRAV20*01": ("VSGLRG", "LYSAGEE"),
    "TRAV21*01": ("DSAIYN", "IQSSQRE"),
    "TRAV22*01": ("DSVNN", "IPSGT"),
    "TRAV23/DV6*01": ("NTAFDY", "IRPDVSE"),
    "TRAV24*01": ("SSNFYA", "MTLNGDE"),
    "TRAV25*01": ("TTLSN", "LVKSGEV"),
    "TRAV26-1*01": ("TISGNEY", "GLKNN"),
    "TRAV26-2*01": ("TISGTDY", "GLTSN"),
    "TRAV27*01": ("SVFSS", "VVTGGEV"),
    "TRAV29/DV5*01": ("NSMFDY", "ISSIKDK"),
    "TRAV3*01": ("VSGNPY", "YITGDNLV"),
    "TRAV30*01": ("KALYS", "LLKGGEQ"),
    "TRAV34*01": ("KTLYG", "LQKGGEE"),
    "TRAV35*01": ("SIFNT", "LYKAGEL"),
    "TRAV36/DV7*01": ("VTNFRS", "LTSSGIE"),
    "TRAV38-1*01": ("TSENNYY", "QEAYKQQN"),
    "TRAV38-2/DV8*01": ("TSESDYY", "QEAYKQQN"),
    "TRAV39*01": ("TTSDR", "LLSNGAV"),
    "TRAV4*01": ("NIATNDY", "GYKTK"),
    "TRAV5*01": ("DSSSTY", "IFSNMDM"),
    "TRAV6*01": ("NYSPAY", "IRENEKE"),
    "TRAV8-1*01": ("YGGTVN", "YFSGDPLV"),
    "TRAV8-2*01": ("SSYSPS", "YTSAATLV"),
    "TRAV8-3*01": ("YGATPY", "YFSGDTLV"),
    "TRAV8-4*01": ("SSVPPY", "YTSAATLV"),
    "TRAV8-6*01": ("SSVSVY", "YLSGSTLV"),
    "TRAV9-2*01": ("ATGYPS", "ATKADDK"),
    "TRBV10-1*01": ("WNHNN", "SYGVQD"),
    "TRBV10-2*01": ("WSHSY", "SAAADI"),
    "TRBV10-3*01": ("ENHRY", "SYGVKD"),
    "TRBV11-1*01": ("SGHAT", "FQDESV"),
    "TRBV11-2*01": ("SGHAT", "FQNNGV"),
    "TRBV11-3*01": ("SGHNT", "YENEEA"),
    "TRBV12-1*01": ("SGHND", "FCSWTL"),
    "TRBV12-5*01": ("LGHNT", "FRNRAP"),
    "TRBV13*01": ("PRHDT", "FYEKMQ"),
    "TRBV14*01": ("SGHDN", "FVKESK"),
    "TRBV15*01": ("LNHNV", "YYDKDF"),
    "TRBV16*01": ("KGHSY", "FQNENV"),
    "TRBV18*01": ("KGHSH", "LQKENI"),
    "TRBV19*01": ("LNHDA", "SQIVND"),
    "TRBV2*01": ("SNHLY", "FYNNEI"),
    "TRBV20-1*01": ("DFQATT", "SNEGSKA"),
    "TRBV24-1*01": ("KGHDR", "SFDVKD"),
    "TRBV25-1*01": ("MGHDK", "SYGVNS"),
    "TRBV27*01": ("MNHEY", "SMNVEV"),
    "TRBV28*01": ("MDHEN", "SYDVKM"),
    "TRBV29-1*01": ("SQVTM", "ANQGSEA"),
    "TRBV3-1*01": ("LGHDT", "YNNKEL"),
    "TRBV30*01": ("GTSNPN", "SVGIG"),
    "TRBV4-1*01": ("MGHRA", "YSYEKL"),
    "TRBV4-2*01": ("LGHNA", "YNFKEQ"),
    "TRBV4-3*01": ("LGHNA", "YSLEER"),
    "TRBV5-1*01": ("SGHRS", "YFSETQ"),
    "TRBV5-4*01": ("SGHNT", "YYREEE"),
    "TRBV5-5*01": ("SGHKS", "YYEKEE"),
    "TRBV5-6*01": ("SGHDT", "YYEEEE"),
    "TRBV5-8*01": ("SGHTS", "YDEGEE"),
    "TRBV6-1*01": ("MNHNS", "SASEGT"),
    "TRBV6-2*01": ("MNHEY", "SVGEGT"),
    "TRBV6-4*01": ("MRHNA", "SNTAGT"),
    "TRBV6-5*01": ("MNHEY", "SVGAGI"),
    "TRBV6-6*01": ("MNHNY", "SVGAGI"),
    "TRBV7-1*01": ("SGHNA", "FQGKDA"),
    "TRBV7-2*01": ("SGHTA", "FQGNSA"),
    "TRBV7-3*01": ("SGHTA", "FQGTGA"),
    "TRBV7-6*01": ("SGHVS", "FNYEAQ"),
    "TRBV7-8*01": ("SGHVS", "FQNEAQ"),
    "TRBV7-9*01": ("SEHNR", "FQNEAQ"),
    "TRBV9*01": ("SGDLS", "YYNGEE"),
}

_TRP = re.compile(r"W[YLF][QKR]")
_FR4_LEN = 11  # IMGT FR4 118–128


def _cell(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and np.isnan(val):
        return ""
    return str(val)


def _find_germline_cdrs(
    v: str, vgene: str
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    pair = _GERMLINE_CDR.get(_cell(vgene))
    if not pair or not v:
        return None
    c1, c2 = pair
    i1 = v.find(c1)
    if i1 < 0:
        return None
    i2 = v.find(c2, i1 + len(c1))
    if i2 < 0:
        i2 = v.find(c2)
        if i2 < 0 or i2 <= i1:
            return None
    return (i1, i1 + len(c1)), (i2, i2 + len(c2))


def _cys23_trp41(v: str) -> tuple[int, int] | None:
    """Cys23 = last Cys 8–22 residues before conserved Trp41."""
    for m in _TRP.finditer(v):
        w41 = m.start()
        lo, hi = max(0, w41 - 22), max(0, w41 - 8)
        cys = [i for i, ch in enumerate(v[lo:hi], start=lo) if ch == "C"]
        if cys:
            return cys[-1], w41
    c23 = v.find("C")
    w = v.find("W", c23 + 8 if c23 >= 0 else 8)
    if c23 >= 0 and w > c23:
        return c23, w
    return None


def _motif_slices(v: str) -> dict[str, str]:
    out = {k: "" for k in ("fr1", "cdr1", "fr2", "cdr2", "fr3")}
    anchors = _cys23_trp41(v)
    if anchors is None:
        out["fr1"] = v
        return out
    c23, w41 = anchors
    fr1_end = min(len(v), c23 + 4)
    fr2_start = max(fr1_end, w41 - 2)
    out["fr1"] = v[:fr1_end]
    out["cdr1"] = v[fr1_end:fr2_start]
    fr2_end = min(len(v), fr2_start + 17)
    out["fr2"] = v[fr2_start:fr2_end]
    rest = v[fr2_end:]
    if len(rest) <= 4:
        out["cdr2"] = rest
        return out
    cdr2_len = min(10, max(4, len(rest) - 32))
    out["cdr2"] = rest[:cdr2_len]
    out["fr3"] = rest[cdr2_len:]
    return out


def split_chain(seq: str, cdr3: str, vgene: str = "") -> dict[str, str]:
    """Return FR/CDR pieces for one TCR chain. Empty strings if missing."""
    seq = _cell(seq)
    cdr3 = _cell(cdr3)
    out = {k: "" for k in ("fr1", "cdr1", "fr2", "cdr2", "fr3", "cdr3", "fr4", "full")}
    out["full"] = seq
    if not seq:
        return out
    if cdr3 and cdr3 in seq:
        start = seq.find(cdr3)
        out["cdr3"] = cdr3
        v = seq[:start]
        out["fr4"] = seq[start + len(cdr3) : start + len(cdr3) + _FR4_LEN]
    else:
        v = seq[:90]
        out["cdr3"] = ""
        out["fr4"] = seq[90 : 90 + _FR4_LEN]
    germ = _find_germline_cdrs(v, vgene)
    if germ is not None:
        (a1, b1), (a2, b2) = germ
        out["fr1"] = v[:a1]
        out["cdr1"] = v[a1:b1]
        out["fr2"] = v[b1:a2]
        out["cdr2"] = v[a2:b2]
        out["fr3"] = v[b2:]
        return out
    out.update(_motif_slices(v))
    return out


def region_text(seq: str, cdr3: str, region: str, vgene: str = "") -> str:
    parts = split_chain(seq, cdr3, vgene)
    if region == "full" or region == "mask":
        return parts["full"]
    if region == "all_cdr":
        return parts["cdr1"] + parts["cdr2"] + parts["cdr3"]
    if region == "all_fr":
        return parts["fr1"] + parts["fr2"] + parts["fr3"] + parts["fr4"]
    return parts.get(region, parts["full"])


def region_indices(
    seq: str, region: str, *, cdr3: str = "", vgene: str = ""
) -> np.ndarray:
    """Residue indices in ``seq`` for a CDR/FR/groove slice (ESM cache is full-chain)."""
    seq = _cell(seq)
    n = len(seq)
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    if region in {"full", "mask", ""}:
        return np.arange(n, dtype=np.int64)
    if region == "groove_a1a2":
        if n > 40:
            return np.arange(24, min(204, n), dtype=np.int64)
        return np.arange(n, dtype=np.int64)
    parts = split_chain(seq, cdr3, vgene)
    names = {
        "all_cdr": ("cdr1", "cdr2", "cdr3"),
        "all_fr": ("fr1", "fr2", "fr3", "fr4"),
    }.get(region, (region,))
    idx: list[int] = []
    cursor = 0
    for name in names:
        piece = parts.get(name, "")
        if not piece:
            continue
        start = seq.find(piece, cursor if name != "cdr3" else 0)
        if start < 0:
            start = seq.find(piece)
        if start < 0:
            continue
        idx.extend(range(start, start + len(piece)))
        cursor = start + len(piece)
    if not idx:
        return np.arange(n, dtype=np.int64)
    return np.asarray(idx, dtype=np.int64)


def chain_region_from_row(row: pd.Series, chain: str, region: str) -> str:
    prefix = "tcra" if chain == "a" else "tcrb"
    return region_text(
        _cell(row.get(f"{prefix}_seq")),
        _cell(row.get(f"{prefix}_seq_cdr3")),
        region,
        _cell(row.get(f"{prefix}_vgene")),
    )


def _onehot(name: str, index: dict[str, int], n: int) -> np.ndarray:
    vec = np.zeros(n, dtype=np.float64)
    i = index.get(_cell(name))
    if i is not None:
        vec[i] = 1.0
    return vec


def vj_onehot_from_row(row: pd.Series, *, alpha: bool, beta: bool) -> np.ndarray:
    """TRAV/TRAJ and/or TRBV/TRBJ one-hot. Unknown alleles stay zero."""
    parts: list[np.ndarray] = []
    if alpha:
        parts.append(
            _onehot(_cell(row.get("tcra_vgene")), _TRAV_INDEX, len(TRAV_ALLELES))
        )
        parts.append(
            _onehot(_cell(row.get("tcra_jgene")), _TRAJ_INDEX, len(TRAJ_ALLELES))
        )
    if beta:
        parts.append(
            _onehot(_cell(row.get("tcrb_vgene")), _TRBV_INDEX, len(TRBV_ALLELES))
        )
        parts.append(
            _onehot(_cell(row.get("tcrb_jgene")), _TRBJ_INDEX, len(TRBJ_ALLELES))
        )
    if not parts:
        return np.zeros(1, dtype=np.float64)
    return np.concatenate(parts)


def gene_index(name: str, which: str) -> int:
    """0 = unknown / padding; 1..N = known allele."""
    table = {
        "trav": _TRAV_INDEX,
        "trbv": _TRBV_INDEX,
        "traj": _TRAJ_INDEX,
        "trbj": _TRBJ_INDEX,
    }[which]
    i = table.get(_cell(name))
    return 0 if i is None else i + 1
