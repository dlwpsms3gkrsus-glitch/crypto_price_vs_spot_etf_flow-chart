"""Local publish-gate regression tests; never collect data or push to GitHub."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
FILES = ("bitcoin_etf_total_flow.csv", "ethereum_etf_total_flow.csv")


class PublishGateTests(unittest.TestCase):
    def test_workflow_gate(self):
        workflow = (ROOT / ".github/workflows/update_charts.yml").read_text(encoding="utf-8")
        steps = re.split(r"^      - name: ", workflow, flags=re.M)[1:]
        names = [step.splitlines()[0] for step in steps]
        check = names.index("Check ETF data freshness")
        publish = names.index("Commit and push changes")
        self.assertLess(names.index("Run chart generation scripts"), check)
        self.assertLess(check, publish)
        self.assertIn("run: python check_data.py", steps[check])
        self.assertNotRegex(workflow, r"continue-on-error:|if:.*(?:always\(|failure\()")
        self.assertIn("- cron: '10 9 * * *'", workflow)

    def run_case(self, kind="normal", target=0, expected=True):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for index, name in enumerate(FILES):
                rows, age, header = 100, 0, "Date,Total"
                if index == target:
                    if kind == "missing":
                        continue
                    if kind == "empty":
                        (folder / name).write_text("", encoding="utf-8")
                        continue
                    if kind == "short":
                        rows = 99
                    if kind == "stale":
                        age = 7
                    if kind == "boundary":
                        age = 6
                    if kind == "missing_date":
                        header = "Wrong,Total"
                latest = date.today() - timedelta(days=age)
                data = [header] + [f"{latest - timedelta(days=n)},1" for n in range(rows)]
                (folder / name).write_text("\n".join(data) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "check_data.py")], cwd=folder,
                env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                capture_output=True, text=True, encoding="utf-8",
            )
            # Model the default Actions success dependency using a harmless marker.
            marker = folder / "published"
            if result.returncode == 0:
                marker.touch()
            self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)
            self.assertEqual(marker.exists(), expected)

    def test_normal(self):
        self.run_case()


def make_case(kind, target, expected):
    def test(self):
        self.run_case(kind, target, expected)
    return test


for kind in ("stale", "short", "empty", "missing", "missing_date", "boundary"):
    for target, coin in enumerate(("btc", "eth")):
        setattr(PublishGateTests, f"test_{coin}_{kind}", make_case(kind, target, kind == "boundary"))


if __name__ == "__main__":
    unittest.main()
