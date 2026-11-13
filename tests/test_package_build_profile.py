"""Run the real shell producer to its final package gate; never install/upload."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("profile", ["package", "image"])
def test_real_shell_package_producer_selects_package_gate_before_any_delivery(tmp_path, profile):
    project = Path(__file__).resolve().parents[1]
    bins = tmp_path / "bin"
    bins.mkdir()
    trace = tmp_path / "gate.json"
    python = bins / "python"
    python.write_text("#!" + sys.executable + "\n" + """
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
if args and args[0]=='tools/community_release_check.py':
    Path(os.environ['GATE_TRACE']).write_text(json.dumps(args))
    sys.exit(37)
print('{}')
""")
    python.chmod(0o700)
    git = bins / "git"
    git.write_text("#!/bin/sh\ncase \"$1\" in\nlog) echo 1700000000;;\nclone) /bin/mkdir -p \"$5\";;\n*) exit 1;;\nesac\n")
    git.chmod(0o700)
    runtime = tmp_path / "run"
    runtime.mkdir()
    env = dict(os.environ, PATH=str(bins) + os.pathsep + os.defpath,
               RUNNER_TEMP=str(runtime), GITHUB_WORKSPACE=str(project),
               RELEASE_TAG="v0.1.0rc1", RELEASE_PROFILE=profile, GATE_TRACE=str(trace))
    outcome = subprocess.run(["/bin/bash", str(project / "tools/release_package_build.sh")],
                             cwd=project, env=env, capture_output=True, timeout=15)
    assert outcome.returncode == 37, outcome.stderr.decode()
    args = json.loads(trace.read_text())
    assert args[args.index("--profile") + 1] == "package"
    assert "--audit-only" not in args and "--dist" in args
    assert not (runtime / "release-packages").exists()
