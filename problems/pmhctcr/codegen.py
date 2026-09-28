"""Render a genotype as an executable Python child program.

The mutator still edits JSON (one TZ operator). This module turns that JSON
into a Python script whose ``entrypoint()`` trains exactly the modules
``describe_compiled`` reports — so the next evolution iteration evaluates
Python, not a silent JSON interpreter.
"""

from __future__ import annotations

import ast
from typing import Any

try:
    from problems.pmhctcr.compiler import describe_compiled
    from problems.pmhctcr.genotype import Genotype, dumps, loads
except ImportError:
    from compiler import describe_compiled
    from genotype import Genotype, dumps, loads

_GENOTYPE_ASSIGN = "GENOTYPE_JSON"


def loads_program(code: str) -> Genotype:
    """Read a child that is either raw JSON or generated Python."""
    text = (code or "").strip()
    if not text:
        raise ValueError("empty program")
    if text.startswith("{") or text.startswith("["):
        return loads(text)
    tree = ast.parse(code)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if _GENOTYPE_ASSIGN not in names:
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, str):
            raise TypeError(f"{_GENOTYPE_ASSIGN} must be a JSON string")
        return loads(value)
    raise ValueError(f"generated program has no {_GENOTYPE_ASSIGN}")


def _py_comment(label: str, text: str) -> str:
    """One Python comment line. LLM substitutes often end with a markdown `---`."""
    one = " ".join(str(text or "").replace("\r", "\n").split())
    one = one.split(" ---", 1)[0].strip(" -")
    return f"# {label}: {one}" if one else f"# {label}:"


def _runtime_lines(g: Genotype, insight: str | None) -> list[str]:
    spec = describe_compiled(g)
    seq = "off"
    if spec["learned_sequence"]:
        seq = str(g.encoders.sequence.arch)
    elif spec["tabular_sequence"] and g.encoders.sequence.arch == "protein_lm":
        seq = "protein_lm_cache"
    elif spec["tabular_sequence"]:
        seq = "bag_of_aa"
    gat = "off"
    if spec["learned_gat"]:
        gat = str(g.encoders.structure.arch)
        if gat == "se3_transformer":
            gat = "distance_kernel"
    cross = spec.get("cross_kind") or "off"
    if spec.get("learned_siamese"):
        extra = "siamese_80d"
        cross = extra if cross == "off" else f"{cross}+{extra}"
    tabs = [
        n
        for n, flag in (
            ("sequence", spec["tabular_sequence"]),
            ("surface", spec["tabular_surface"]),
            ("structure", spec["tabular_structure"]),
        )
        if flag
    ]
    spots = (
        f"spots L2<{g.encoders.surface.spots.threshold:g}"
        if g.encoders.surface.spots.enabled
        else "spots off"
    )
    lines = [
        _py_comment("insight", insight)
        if insight and str(insight).strip()
        else "# insight: (unguided)",
        f"# head: {spec['head']}",
        f"# SeqEncoder: {seq}",
        f"# GAT: {gat}",
        f"# cross_attn: {cross}",
        f"# tabular: {', '.join(tabs) or 'none'}; {spots}",
        f"# model.type: {g.model.type}  layers={g.model.num_layers}  hid={g.model.hidden_dim}",
    ]
    for item in spec["ignored"]:
        lines.append(_py_comment("ignored", item))
    return lines


def render_program(g: Genotype, *, insight: str | None = None) -> str:
    """Python source: GENOTYPE_JSON + entrypoint() → compile_genotype."""
    header = "\n".join(_runtime_lines(g, insight))
    payload = dumps(g)
    return (
        '"""pMHC-TCR child generated from a JSON genotype. Do not hand-edit."""\n'
        "from __future__ import annotations\n\n"
        f"{_GENOTYPE_ASSIGN} = {payload!r}\n\n"
        f"{header}\n\n"
        "def entrypoint():\n"
        "    try:\n"
        "        from problems.pmhctcr.compiler import compile_genotype\n"
        "    except ImportError:\n"
        "        from compiler import compile_genotype\n"
        f"    return compile_genotype({_GENOTYPE_ASSIGN})\n"
    )


def exec_program(source: str) -> Any:
    """Compile and run ``entrypoint()`` from generated (or hand-written) Python."""
    ns: dict[str, Any] = {}
    exec(compile(source, "<pmhctcr_child>", "exec"), ns, ns)
    fn = ns.get("entrypoint")
    if not callable(fn):
        raise ValueError("generated program has no entrypoint()")
    obj = fn()
    try:
        setattr(obj, "__genome_source__", source)
    except Exception:
        pass
    return obj
