"""ColBERT search server — loads index once, serves batch queries via HTTP.

Loads the ColBERT Searcher in-process (with GPU if available) and exposes a
minimal FastAPI HTTP interface.  exec_runner workers query it instead of each
loading the 15-20 GB index independently.

Single-GPU usage (original behaviour):
    PYTHONPATH=<repo> python experiments/hotpotqa/tools/colbert_server.py \
        --index-dir experiments/hotpotqa/indexes/colbert_index \
        --port 8889 [--host 0.0.0.0]

Multi-GPU usage (N workers, one per GPU, router on --port):
    PYTHONPATH=<repo> python experiments/hotpotqa/tools/colbert_server.py \
        --index-dir experiments/hotpotqa/indexes/colbert_index \
        --port 8889 --num-gpus 8 [--gpu-ids 0,1,2,3,4,5,6,7]

    Workers bind to ports --port+1 … --port+N.  The ColBERT index is
    mmap-backed so the OS shares physical pages across workers; total extra
    RAM per additional worker is ~1-2 GB (model weights + Python overhead).

API:
    GET  /health  → {"status": "ok", "passages": N[, "workers": W]}
    POST /search  {"queries": ["q1", "q2", ...], "k": 7}
                → {"results": ["[1] p1\\n[2] p2...", ...]}
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import threading

from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel
import uvicorn

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    queries: list[str]
    k: int = 7


# ===========================================================================
# WORKER APP  (single GPU — used in worker mode and num-gpus=1 mode)
# ===========================================================================

worker_app = FastAPI()
_searcher = None
_collection = None
_ready = threading.Event()
_search_lock = threading.Lock()  # ColBERT Searcher is not thread-safe


@worker_app.get("/health")
def health():
    if not _ready.is_set():
        raise HTTPException(status_code=503, detail="index not loaded yet")
    return {"status": "ok", "passages": len(_collection)}


@worker_app.post("/search")
def search(req: SearchRequest):
    if not _ready.is_set():
        raise HTTPException(status_code=503, detail="index not loaded yet")
    k = max(1, req.k)
    # ncells/ndocs pre-configured at load time to paper's BEIR values
    # (ncells=2, ndocs=8192). search_k=max(k,100) stays in the k≤100 branch
    # of dense_search() while the pre-configured ndocs override its default.
    search_k = max(k, 100)
    results: list[str] = []
    with _search_lock:
        for query in req.queries:
            pids, _ranks, _scores = _searcher.search(query, k=search_k)
            passages = [_collection[pid] for pid in pids[:k]]
            results.append("\n".join(f"[{i + 1}] {p}" for i, p in enumerate(passages)))
    return {"results": results}


def _load(index_dir: Path, checkpoint: str) -> None:
    """Load ColBERT Searcher in a background thread; set _ready when done."""
    global _searcher, _collection

    from colbert import Searcher
    from colbert.infra import ColBERTConfig, Run, RunConfig

    gpu = os.environ.get("CUDA_VISIBLE_DEVICES", "unset")
    print(f"[colbert_server] Loading index from {index_dir}  (GPU={gpu}) …", flush=True)

    # ColBERT resolves index to {root}/{experiment}/indexes/{name}.
    colbert_resolved = index_dir.parent / "hotpotqa" / "indexes" / index_dir.name
    if not colbert_resolved.exists():
        raise FileNotFoundError(
            f"ColBERT index not found at {colbert_resolved} "
            f"(resolved from index_dir={index_dir})"
        )

    with Run().context(RunConfig(nranks=1, experiment="hotpotqa")):
        config = ColBERTConfig(
            root=str(index_dir.parent),
            index_root=str(index_dir.parent),
        )
        _searcher = Searcher(
            index=index_dir.name,
            config=config,
            checkpoint=checkpoint,
        )

    _collection = _searcher.collection

    # Fix search parameters to match ColBERTv2 paper (Appendix F) BEIR settings:
    #   probe (ncells) = 2, candidates (ndocs) = probe × 2^12 = 8192
    _searcher.configure(ncells=2, centroid_score_threshold=0.45, ndocs=8192)

    _ready.set()
    print(
        f"[colbert_server] Ready (GPU={gpu}) — {len(_collection):,} passages loaded.",
        flush=True,
    )


# ===========================================================================
# PROXY APP  (multi-GPU router — only used when num-gpus > 1)
# ===========================================================================

proxy_app = FastAPI()

# Populated in main() before proxy_app starts
_worker_urls: list[str] = []
_inflight: list[int] = []  # in-flight request count per worker
_alive: list[bool] = []  # worker health state
_routing_lock = threading.Lock()
_proxy_client: httpx.AsyncClient | None = None


@proxy_app.on_event("startup")
async def _proxy_startup():
    global _proxy_client
    _proxy_client = httpx.AsyncClient(timeout=120.0)


@proxy_app.on_event("shutdown")
async def _proxy_shutdown():
    if _proxy_client:
        await _proxy_client.aclose()


@proxy_app.get("/health")
async def proxy_health():
    errors = []
    passages = None
    for i, url in enumerate(_worker_urls):
        try:
            r = await _proxy_client.get(f"{url}/health", timeout=5.0)
            if r.status_code == 200:
                _alive[i] = True
                passages = r.json().get("passages", passages)
            else:
                errors.append(f"worker {i}: HTTP {r.status_code}")
                _alive[i] = False
        except Exception as exc:
            errors.append(f"worker {i}: {exc}")
            _alive[i] = False
    if errors:
        raise HTTPException(status_code=503, detail=errors)
    return {"status": "ok", "passages": passages, "workers": len(_worker_urls)}


def _pick_worker() -> int:
    """Least-connections routing — pick the worker with fewest in-flight requests."""
    with _routing_lock:
        best = -1
        best_count = float("inf")
        for i, (alive, count) in enumerate(zip(_alive, _inflight)):
            if alive and count < best_count:
                best, best_count = i, count
        if best == -1:
            raise RuntimeError("No healthy workers available")
        _inflight[best] += 1
    return best


@proxy_app.post("/search")
async def proxy_search(req: SearchRequest):
    try:
        idx = _pick_worker()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    url = _worker_urls[idx]
    try:
        r = await _proxy_client.post(f"{url}/search", json=req.model_dump())
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        _alive[idx] = False  # assume unhealthy on error
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
    except Exception as exc:
        _alive[idx] = False
        raise HTTPException(status_code=502, detail=str(exc))
    finally:
        with _routing_lock:
            _inflight[idx] = max(0, _inflight[idx] - 1)


# ---------------------------------------------------------------------------
# Background health-monitor: re-checks dead workers every 30 s
# ---------------------------------------------------------------------------


async def _health_monitor():
    while True:
        await asyncio.sleep(30)
        for i, url in enumerate(_worker_urls):
            if not _alive[i]:
                try:
                    r = await _proxy_client.get(f"{url}/health", timeout=5.0)
                    if r.status_code == 200:
                        _alive[i] = True
                        print(
                            f"[colbert_router] Worker {i} recovered: {url}", flush=True
                        )
                except Exception:
                    pass


@proxy_app.on_event("startup")
async def _start_monitor():
    asyncio.create_task(_health_monitor())


# ===========================================================================
# Entry point
# ===========================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="ColBERT search server")
    parser.add_argument(
        "--index-dir",
        required=True,
        type=Path,
        help="Path to the virtual ColBERT index dir (e.g. experiments/colbert_index). "
        "Actual index lives at <parent>/hotpotqa/indexes/<name>/.",
    )
    parser.add_argument(
        "--checkpoint",
        default="colbert-ir/colbertv2.0",
        help="HuggingFace checkpoint or local path (default: colbert-ir/colbertv2.0)",
    )
    parser.add_argument("--port", type=int, default=8889)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--num-gpus",
        type=int,
        default=1,
        help="Number of GPU worker replicas (default: 1). "
        "Workers bind to --port+1 … --port+N; the router listens on --port.",
    )
    parser.add_argument(
        "--gpu-ids",
        default=None,
        help="Comma-separated GPU IDs to use (default: 0,1,…,num-gpus-1). "
        "Must have exactly --num-gpus entries.",
    )
    # Internal flag — set when spawning worker subprocesses; not shown in help.
    parser.add_argument(
        "--worker-gpu-id", type=int, default=None, help=argparse.SUPPRESS
    )

    args = parser.parse_args()

    # ── Worker subprocess mode ────────────────────────────────────────────────
    if args.worker_gpu_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.worker_gpu_id)
        t = threading.Thread(
            target=_load, args=(args.index_dir, args.checkpoint), daemon=True
        )
        t.start()
        uvicorn.run(worker_app, host=args.host, port=args.port, log_level="warning")
        return

    # ── Single-GPU mode (original behaviour) ─────────────────────────────────
    if args.num_gpus == 1:
        t = threading.Thread(
            target=_load, args=(args.index_dir, args.checkpoint), daemon=True
        )
        t.start()
        uvicorn.run(worker_app, host=args.host, port=args.port, log_level="warning")
        return

    # ── Multi-GPU router mode ─────────────────────────────────────────────────
    gpu_ids = (
        [int(x) for x in args.gpu_ids.split(",")]
        if args.gpu_ids
        else list(range(args.num_gpus))
    )
    if len(gpu_ids) != args.num_gpus:
        parser.error(
            f"--gpu-ids has {len(gpu_ids)} entries but --num-gpus={args.num_gpus}"
        )

    base_port = args.port + 1
    procs: list[subprocess.Popen] = []

    # Workers bind on the same interface as the router, but the proxy connects to
    # them via 127.0.0.1 (loopback) — 0.0.0.0 is a valid bind address but not a
    # connectable target for outbound connections.
    worker_connect_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host

    env_base = os.environ.copy()
    env_base.pop("CUDA_VISIBLE_DEVICES", None)  # each worker sets its own

    for i, gpu_id in enumerate(gpu_ids):
        worker_port = base_port + i
        cmd = [
            sys.executable,
            __file__,
            "--index-dir",
            str(args.index_dir),
            "--checkpoint",
            args.checkpoint,
            "--host",
            args.host,
            "--port",
            str(worker_port),
            "--worker-gpu-id",
            str(gpu_id),
        ]
        p = subprocess.Popen(cmd, env=env_base)
        procs.append(p)
        _worker_urls.append(f"http://{worker_connect_host}:{worker_port}")
        _inflight.append(0)
        _alive.append(False)
        print(
            f"[colbert_router] Spawned worker {i}: GPU={gpu_id} port={worker_port} pid={p.pid}",
            flush=True,
        )

    # Wait for all workers to pass /health before opening the router port.
    print(
        f"[colbert_router] Waiting for {args.num_gpus} workers to load index…",
        flush=True,
    )

    async def _await_workers():
        async with httpx.AsyncClient(timeout=300.0) as client:
            for i, url in enumerate(_worker_urls):
                while True:
                    # Check the worker process is still alive
                    if procs[i].poll() is not None:
                        raise RuntimeError(
                            f"Worker {i} (GPU={gpu_ids[i]}) died before becoming ready "
                            f"(exit code {procs[i].returncode})"
                        )
                    try:
                        r = await client.get(f"{url}/health", timeout=5.0)
                        if r.status_code == 200:
                            _alive[i] = True
                            print(
                                f"[colbert_router] Worker {i} ready: {url}", flush=True
                            )
                            break
                    except Exception:
                        pass
                    await asyncio.sleep(2)

    try:
        asyncio.run(_await_workers())
    except RuntimeError as exc:
        print(f"[colbert_router] FATAL: {exc}", flush=True)
        for p in procs:
            p.terminate()
        sys.exit(1)

    print(
        f"[colbert_router] All {args.num_gpus} workers ready. "
        f"Router listening on {args.host}:{args.port}.",
        flush=True,
    )

    try:
        uvicorn.run(proxy_app, host=args.host, port=args.port, log_level="warning")
    finally:
        print("[colbert_router] Shutting down workers…", flush=True)
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()


if __name__ == "__main__":
    main()
