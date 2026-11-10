import unittest
from uniconvert.formats import get_registry, categorise


class TestFormats(unittest.TestCase):
    def test_loads_pairs(self):
        reg = get_registry()
        self.assertGreater(len(reg.pairs), 200)

    def test_audio_targets(self):
        reg = get_registry()
        tgts = reg.targets_for("mp3")
        for t in ("mp4", "wav", "flac", "aac", "ogg"):
            self.assertIn(t, tgts)

    def test_image_pair(self):
        reg = get_registry()
        self.assertTrue(reg.is_supported("jpg", "png"))
        self.assertTrue(reg.is_supported("png", "jpg"))
        self.assertTrue(reg.is_supported("webp", "jpg"))

    def test_document_pair(self):
        reg = get_registry()
        self.assertTrue(reg.is_supported("pdf", "docx"))
        self.assertTrue(reg.is_supported("docx", "pdf"))

    def test_categorise(self):
        self.assertEqual(categorise("mp3"), "audio")
        self.assertEqual(categorise("mp4"), "video")
        self.assertEqual(categorise("png"), "image")
        self.assertEqual(categorise("docx"), "document")
        self.assertEqual(categorise("zip"), "archive")
        self.assertEqual(categorise("epub"), "ebook")
        self.assertEqual(categorise("py"), "code")


if __name__ == "__main__":
    unittest.main()
