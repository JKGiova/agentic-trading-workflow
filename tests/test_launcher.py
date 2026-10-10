"""Exercise Bash bootstrap/dispatch offline; no installer or provider network calls."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Bash launcher requires Bash")

FAKE_UV = """#!/bin/sh
printf '%s\\n' "$PWD" "$@" >> "$LAUNCH_LOG"
printf '%s\\n' '--end--' >> "$LAUNCH_LOG"
if [ "$1" = sync ]; then exit "${SYNC_EXIT:-0}"; fi
exit "${APP_EXIT:-0}"
"""


def executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


@pytest.fixture
def launcher(tmp_path):
    project = tmp_path / "project with spaces"
    project.mkdir()
    shutil.copy2(ROOT / "start.sh", project / "start.sh")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # A controlled PATH exercises machines with no uv and no network clients.
    for name in ("dirname", "mktemp", "rm", "sh", "mkdir", "cp", "chmod"):
        tool = shutil.which(name)
        assert tool is not None
        (bin_dir / name).symlink_to(tool)
    environment = {
        "PATH": str(bin_dir),
        "HOME": str(tmp_path / "empty home"),
        "TMPDIR": str(tmp_path),
        "LAUNCH_LOG": str(tmp_path / "calls"),
    }

    def run(*args, **overrides):
        return subprocess.run(
            [BASH, str(project / "start.sh"), *args],
            cwd=tmp_path,
            env=environment | overrides,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    return project, bin_dir, environment, run


@pytest.mark.parametrize("args", [(), ("--config", "config with spaces.json", "--doctor")])
def test_existing_uv_defaults_and_argument_forwarding(launcher, args):
    project, bin_dir, environment, run = launcher
    executable(bin_dir / "uv", FAKE_UV)
    result = run(*args, TRADEBOT_PYTHON="3.13", APP_EXIT="7")
    assert result.returncode == 7
    calls = Path(environment["LAUNCH_LOG"]).read_text().split("--end--\n")
    assert calls[0].splitlines() == [
        str(project),
        "sync",
        "--locked",
        "--no-dev",
        "--inexact",
        "--python",
        "3.13",
    ]
    assert calls[1].splitlines() == [
        str(project),
        "run",
        "--no-sync",
        "tradebot",
        *args,
    ]
    assert result.stdout == ""


def test_sync_failure_does_not_launch_app(launcher):
    _, bin_dir, environment, run = launcher
    executable(bin_dir / "uv", FAKE_UV)
    result = run(SYNC_EXIT="4")
    assert result.returncode == 4
    assert "tradebot" not in Path(environment["LAUNCH_LOG"]).read_text().splitlines()


@pytest.mark.parametrize("client", ["curl", "wget"])
def test_bootstrap_and_reuse_local_uv_without_network(launcher, client):
    project, bin_dir, environment, run = launcher
    payload = bin_dir / "uv-payload"
    executable(payload, FAKE_UV)
    installer = bin_dir / "installer-payload"
    installer.write_text(
        '#!/bin/sh\nmkdir -p "$UV_UNMANAGED_INSTALL"\n'
        'cp "$UV_PAYLOAD" "$UV_UNMANAGED_INSTALL/uv"\n'
        'chmod +x "$UV_UNMANAGED_INSTALL/uv"\n'
    )
    executable(
        bin_dir / client,
        "#!/bin/sh\nfor arg do\n"
        '  if [ "${next:-0}" = 1 ]; then target="$arg"; next=0; fi\n'
        '  case "$arg" in --output) next=1;; --output-document=*) target="${arg#*=}";; esac\n'
        'done\ncp "$INSTALLER_PAYLOAD" "$target"\n',
    )
    result = run("--demo", "--doctor", UV_PAYLOAD=str(payload), INSTALLER_PAYLOAD=str(installer))
    assert result.returncode == 0, result.stderr
    assert (project / ".tradebot/tools/uv").is_file()
    assert not list(project.parent.glob("tradebot-uv.*"))
    (bin_dir / client).unlink()
    assert run("--demo", "--doctor").returncode == 0
    assert Path(environment["LAUNCH_LOG"]).read_text().count("--end--") == 4


def test_failed_download_is_cleaned_up(launcher):
    project, bin_dir, _, run = launcher
    executable(bin_dir / "curl", "#!/bin/sh\nexit 22\n")
    result = run()
    assert result.returncode == 22
    assert not (project / ".tradebot/tools/uv").exists()
    assert not list(project.parent.glob("tradebot-uv.*"))


def test_missing_download_client_has_actionable_message(launcher):
    _, _, _, run = launcher
    result = run()
    assert result.returncode == 1
    assert "Install curl or wget" in result.stderr
