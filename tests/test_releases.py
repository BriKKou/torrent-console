import unittest

from releases import describe


class DescribeTest(unittest.TestCase):
    def test_movie(self):
        info = describe("Anniversary.2025.MULTI.VFF.2160p.WEBRip.DV.HDR10Plus.AC3.5.1.x265-Neostark")
        self.assertEqual((info.name, info.year, info.resolution, info.source), ("Anniversary", "2025", "2160p", "WEBRip"))
        self.assertEqual(info.langs, ("MULTI", "VFF"))
        self.assertEqual((info.hdr, info.codec), (("DV", "HDR10+"), "H265"))

    def test_year_in_title(self):
        info = describe("Blade.Runner.2049.2017.MULTi.TRUEFRENCH.2160p.BluRay.REMUX.HDR.HEVC-GRP")
        self.assertEqual((info.name, info.year, info.source), ("Blade Runner 2049", "2017", "Remux"))

    def test_title_starting_with_year(self):
        self.assertEqual(describe("1917.2019.MULTi.VF2.1080p.BluRay.HDLight.x265-NOTAG").name, "1917")

    def test_series(self):
        info = describe("Lupin.S03E05.MULTI.VFF.1080p.WEB.EAC3.x264-cakes")
        self.assertEqual((info.name, info.season, info.source, info.codec), ("Lupin", "S03E05", "WEB-DL", "H264"))

    def test_unknown_quality(self):
        info = describe("Un.Film.Sans.Tags")
        self.assertEqual((info.resolution, info.source, info.langs), ("SD", "Autre", ()))


if __name__ == "__main__":
    unittest.main()
