import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from uniconvert.cli import main


class TestCLI(unittest.TestCase):
    def test_csv_to_json_cli(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.csv"
            src.write_text("x,y\n1,2\n", encoding="utf-8")
            buf = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err):
                rc = main([str(src), "--to", "json", "--out", td])
            self.assertEqual(rc, 0)
            out = Path(td) / "a.json"
            self.assertTrue(out.exists())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["x"], "1")

    def test_list_formats(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--list-formats", "--to", "mp3", "dummy"])
        # Should not crash; list mode handles extra files
        # (argparse will consume them as positional)


if __name__ == "__main__":
    unittest.main()
