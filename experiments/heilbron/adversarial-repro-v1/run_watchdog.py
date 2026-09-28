"""
DEPRECATED: Use the CLI watchdog instead:
    gigaevo -e heilbron/adversarial-repro-v1 watchdog

The CLI handles PYTHONPATH, NO_PROXY, and plugin resolution automatically.
This script is kept for backwards compatibility with existing experiments.
"""

from pathlib import Path
import sys

PROJ = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJ))

EXP_NAME = "heilbron/adversarial-repro-v1"

from gigaevo.experiment.manifest import ExperimentManifest  # noqa: E402
from gigaevo.monitoring.experiment_monitor import RunConfig  # noqa: E402
import gigaevo.monitoring.plugins  # noqa: E402, F401  — trigger plugin registration
from gigaevo.monitoring.run_spec import RunSpec  # noqa: E402
from gigaevo.monitoring.watchdog_config import WatchdogConfig  # noqa: E402
from gigaevo.monitoring.watchdog_engine import WatchdogEngine  # noqa: E402
from gigaevo.monitoring.watchdog_plugin import resolve_plugin  # noqa: E402

manifest = ExperimentManifest.from_yaml_file(
    PROJ / "experiments" / EXP_NAME / "experiment.yaml"
)
PluginClass = resolve_plugin(manifest)

run_configs = [
    RunConfig(
        run_spec=RunSpec(prefix=r.prefix, db=r.db, label=r.label, role=r.role),
        metric_names=[manifest.contract.problem.metric_name or "fitness"],
        pid=r.pid,
    )
    for r in manifest.contract.runs
]

engine = WatchdogEngine(
    experiment_name=EXP_NAME,
    plugin=PluginClass(),
    run_configs=run_configs,
    config=WatchdogConfig(),
    max_generations=manifest.contract.max_generations,
)

if __name__ == "__main__":
    engine.run()
