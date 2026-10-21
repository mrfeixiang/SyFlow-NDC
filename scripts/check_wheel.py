"""Build and test a wheel outside the checkout, using local runtime dependencies."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run(sys.executable, '-m', 'build', '--wheel', '--outdir', str(root / 'dist'))
        run(sys.executable, '-m', 'venv', '--system-site-packages', str(root / 'env'))
        python = root / 'env' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        wheel = next((root / 'dist').glob('*.whl'))
        run(str(python), '-m', 'pip', 'install', '--no-deps', '--force-reinstall', str(wheel), cwd=root)
        run(str(python), '-c',
            'import src; from pathlib import Path; '
            'from src.utils.paths import workspace_root, runs_directory; '
            f'assert Path(src.__file__).is_relative_to(Path({str(root / "env")!r})); '
            'assert workspace_root() == Path.cwd(); '
            'assert runs_directory() == Path.cwd() / "runs"', cwd=root)
        run(str(python), '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-v', cwd=root)
        console = python.parent / ('syflow.exe' if os.name == 'nt' else 'syflow')
        run(str(console), '--help', cwd=root)


if __name__ == '__main__':
    main()
