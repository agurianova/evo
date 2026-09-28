# Search traces

Search logs are not stored in Git. Download the five paper-named archives from
Google Drive:

https://drive.google.com/drive/folders/1cB429RPCAVKbi9GXmarU64Ji5l4WGSNZ?usp=sharing

| Paper name | file |
|---|---|
| Expert-guided | `Expert-guided.tar.gz` |
| Unguided | `Unguided.tar.gz` |
| Plain | `Plain.tar.gz` |
| Memory cards | `Memory-cards.tar.gz` |
| Best-of-N | `Best-of-N.tar.gz` |

Each archive contains five independent runs as `run-1` ??? `run-5`.
System-role prompt bodies in LLM traces are replaced with `[system prompt]`.
Score tables used in the paper stay in `analysis/`.
`scripts/export_mutation_tables.py` rebuilds Appendix H from the Expert-guided traces.
