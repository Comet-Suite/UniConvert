import json
import tempfile
import unittest
from pathlib import Path

from uniconvert.converter import ConversionJob, convert, ConversionError
from uniconvert.formats import get_registry


class TestConverter(unittest.TestCase):
    def test_csv_to_json(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.csv"
            src.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")
            job = ConversionJob(src=src, dst_format="json")
            out = convert(job)
            self.assertTrue(out.exists())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["name"], "Alice")

    def test_json_to_yaml(self):
        try:
            import yaml  # noqa
        except ImportError:
            self.skipTest("PyYAML not installed")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.json"
            src.write_text('{"x":1,"y":[2,3]}', encoding="utf-8")
            job = ConversionJob(src=src, dst_format="yaml")
            out = convert(job)
            self.assertTrue(out.exists())
            self.assertIn("x:", out.read_text(encoding="utf-8"))

    def test_txt_to_html(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.txt"
            src.write_text("hello world", encoding="utf-8")
            job = ConversionJob(src=src, dst_format="html")
            out = convert(job)
            self.assertTrue(out.exists())
            self.assertIn("<html", out.read_text(encoding="utf-8"))

    def test_image_png_to_jpg(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.png"
            Image.new("RGB", (32, 32), (255, 0, 0)).save(src)
            job = ConversionJob(src=src, dst_format="jpg")
            out = convert(job)
            self.assertTrue(out.exists())
            with Image.open(out) as im:
                self.assertEqual(im.format, "JPEG")

    def test_audio_wav_to_mp3(self):
        import shutil
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not installed")
        # Generate a sine wav first via ffmpeg
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "tone.wav"
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                            str(src)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            job = ConversionJob(src=src, dst_format="mp3")
            out = convert(job)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)

    def test_zip_roundtrip(self):
        import zipfile
        with tempfile.TemporaryDirectory() as td:
            src_zip = Path(td) / "in.zip"
            inner = Path(td) / "inner"
            inner.mkdir()
            (inner / "a.txt").write_text("hello", encoding="utf-8")
            with zipfile.ZipFile(src_zip, "w") as z:
                z.write(inner / "a.txt", "a.txt")
            job = ConversionJob(src=src_zip, dst_format="tar")
            out = convert(job)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
