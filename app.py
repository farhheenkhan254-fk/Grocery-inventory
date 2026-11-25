import sys
from pathlib import Path

__path__ = [str(Path(__file__).parent / "app")]

if __name__ == "__main__":
    import runpy
    target = Path(__file__).parent / "app" / "main.py"
    runpy.run_path(str(target), run_name="__main__")
