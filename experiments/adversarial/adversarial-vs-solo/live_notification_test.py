#!/usr/bin/env python3
"""Live integration test for Phase 2 notification channels.

Tests TelegramChannel, GitHubPRChannel, and NotificationDispatcher
against the REAL running adversarial/adversarial-vs-solo experiment.

Usage:
    PYTHONPATH=. python experiments/adversarial/adversarial-vs-solo/live_notification_test.py
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

from dotenv import load_dotenv
import redis

from gigaevo.experiment.manifest import load_manifest
from gigaevo.monitoring.alerts import Alert, AlertSeverity, AlertType
from gigaevo.monitoring.dispatcher import DispatchResult, NotificationDispatcher
from gigaevo.monitoring.github_pr_channel import GitHubPRChannel
from gigaevo.monitoring.notifications import StatusUpdate
from gigaevo.monitoring.redis_queries import collect_snapshot
from gigaevo.monitoring.run_spec import RunSpec
from gigaevo.monitoring.telegram_channel import TelegramChannel

load_dotenv()

EXP = "adversarial/adversarial-vs-solo"


def collect_live_snapshots():
    """Collect real RunSnapshots from Redis for all experiment runs."""
    m = load_manifest(EXP)
    snapshots = []
    for run in m.contract.runs:
        r = redis.Redis(host="localhost", port=6379, db=run.db)
        spec = RunSpec(prefix=run.prefix, db=run.db, label=run.label)
        snap = collect_snapshot(r, spec, metric_names=["fitness"], pid=run.pid)
        snapshots.append(snap)
        print(
            f"  {run.label}: gen={snap.generation} fitness={snap.metrics.get('fitness')}"
        )
    return snapshots, m


def build_status_update(snapshots, manifest):
    """Build a StatusUpdate from live data."""
    test_alert = Alert(
        alert_type=AlertType.COMPLETION,
        severity=AlertSeverity.INFO,
        message="[LIVE TEST] Phase 2 notification system live integration test",
        run_label="ALL",
    )
    return StatusUpdate(
        experiment_name=EXP,
        snapshots=snapshots,
        alerts=[test_alert],
        max_generations=manifest.contract.max_generations,
    )


async def test_telegram(update: StatusUpdate) -> bool:
    """Test TelegramChannel with real Telegram delivery."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        print("  SKIP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False

    channel = TelegramChannel(bot_token=bot_token, chat_id=chat_id)
    try:
        # Health check
        healthy = await channel.check_health()
        print(f"  Health check: {'PASS' if healthy else 'FAIL'}")
        if not healthy:
            return False

        # Send status
        status_ok = await channel.send_status(update)
        print(f"  send_status: {'PASS' if status_ok else 'FAIL'}")

        # Send alert
        alert_ok = await channel.send_alert(update.alerts[0])
        print(f"  send_alert: {'PASS' if alert_ok else 'FAIL'}")

        return status_ok and alert_ok
    finally:
        await channel.close()


async def test_github_pr(update: StatusUpdate) -> bool:
    """Test GitHubPRChannel with real PR #203 comment."""
    gh_token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    if not gh_token:
        print("  SKIP: no gh auth token")
        return False

    m = load_manifest(EXP)
    channel = GitHubPRChannel(
        repo="KhrulkovV/gigaevo-core-internal",
        pr_number=m.pr_number,
        token=gh_token,
        branch="exp/adversarial/adversarial-vs-solo",
    )
    try:
        # Health check
        healthy = await channel.check_health()
        print(f"  Health check: {'PASS' if healthy else 'FAIL'}")
        if not healthy:
            return False

        # Send status (creates/edits rolling comment)
        status_ok = await channel.send_status(update)
        print(f"  send_status (rolling comment): {'PASS' if status_ok else 'FAIL'}")

        # Send alert (creates new comment)
        alert_ok = await channel.send_alert(update.alerts[0])
        print(f"  send_alert (new comment): {'PASS' if alert_ok else 'FAIL'}")

        return status_ok and alert_ok
    finally:
        await channel.close()


async def test_dispatcher(update: StatusUpdate) -> bool:
    """Test NotificationDispatcher fan-out with both channels."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    gh_token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    m = load_manifest(EXP)

    channels = []
    if bot_token and chat_id:
        channels.append(TelegramChannel(bot_token=bot_token, chat_id=chat_id))
    if gh_token:
        channels.append(
            GitHubPRChannel(
                repo="KhrulkovV/gigaevo-core-internal",
                pr_number=m.pr_number,
                token=gh_token,
                branch="exp/adversarial/adversarial-vs-solo",
            )
        )

    if not channels:
        print("  SKIP: no channels available")
        return False

    dispatcher = NotificationDispatcher(channels=channels)
    result: DispatchResult = await dispatcher.dispatch(update)

    print(f"  Channel results: {result.channel_results}")
    print(f"  Alerts sent: {result.alerts_sent}")
    print(f"  Alerts suppressed: {result.alerts_suppressed}")
    print(f"  all_succeeded: {result.all_succeeded}")

    # Cleanup
    for ch in channels:
        if hasattr(ch, "close"):
            await ch.close()

    return result.all_succeeded


async def main():
    print("=" * 70)
    print("LIVE NOTIFICATION TEST — Phase 2 Integration")
    print(f"Experiment: {EXP}")
    print("=" * 70)

    # Step 1: Collect live data
    print("\n1. Collecting live snapshots from Redis...")
    snapshots, manifest = collect_live_snapshots()
    print(f"   {len(snapshots)} runs collected")

    # Step 2: Build StatusUpdate
    print("\n2. Building StatusUpdate...")
    update = build_status_update(snapshots, manifest)
    print(f"   {update.run_count} runs, {len(update.alerts)} alerts")

    results = {}

    # Step 3: Test TelegramChannel
    print("\n3. Testing TelegramChannel (real Telegram delivery)...")
    results["telegram"] = await test_telegram(update)

    # Step 4: Test GitHubPRChannel
    print("\n4. Testing GitHubPRChannel (real PR #203 comment)...")
    results["github_pr"] = await test_github_pr(update)

    # Step 5: Test NotificationDispatcher (fan-out)
    print("\n5. Testing NotificationDispatcher (fan-out to both)...")
    results["dispatcher"] = await test_dispatcher(update)

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    print(f"\nOverall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
    print("=" * 70)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
