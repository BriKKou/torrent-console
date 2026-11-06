"""Lecture des noms de releases (« Film.2024.MULTI.VFF.2160p.WEB-DL.DV.H265-GRP »), commune à toutes les sources."""
import re
from dataclasses import dataclass

LANGS = ("MULTI", "TRUEFRENCH", "VFF", "VFQ", "VFI", "VF2", "VOF", "VF", "FRENCH", "VOSTFR", "SUBFRENCH", "VO")
# Le premier motif qui correspond gagne
SOURCES = (
    ("Remux", "REMUX"),
    ("HDLight", "HDLIGHT|4KLIGHT"),
    ("WEBRip", "WEB-?RIP"),
    ("WEB-DL", "WEB-?DL|WEB"),
    ("BluRay", "BLU-?RAY|BDRIP|BRRIP"),
    ("HDTV", "HDTV"),
    ("DVD", "DVD-?RIP|DVD"),
    ("CAM", "CAM|HDCAM|TS|HDTS|TELESYNC"),
)
RESOLUTIONS = (("2160p", "2160P|4K|UHD"), ("1080p", "1080[PI]"), ("720p", "720P"))
HDR = (("DV", "DV|DOVI"), ("HDR10+", r"HDR10PLUS|HDR10\+"), ("HDR", "HDR10|HDR"))
CODECS = (("H265", r"X265|H\.?265|HEVC"), ("H264", r"X264|H\.?264|AVC"), ("AV1", "AV1"))
# Premier tag technique : ce qui précède est le titre
TECH = re.compile(r"(?<![A-Z0-9])(?:2160P|1080[PI]|720P|4K|UHD|MULTI|TRUEFRENCH|FRENCH|VFF|VFQ|VFI|VF2|VOF|VOSTFR"
                  r"|WEB|WEB-?DL|WEB-?RIP|BLU-?RAY|HDLIGHT|REMUX|HDTV)(?![A-Z0-9])")
YEAR = re.compile(r"(?<![0-9])(?:19|20)[0-9]{2}(?![0-9])")
SEASON = re.compile(r"(?<![A-Z0-9])S[0-9]{1,2}(?:E[0-9]{1,3})?(?![0-9])")


@dataclass(frozen=True)
class ReleaseInfo:
    name: str
    year: str
    season: str
    resolution: str
    langs: tuple[str, ...]
    source: str
    hdr: tuple[str, ...]
    codec: str


def _has(text: str, pattern: str) -> bool:
    return re.search(rf"(?<![A-Z0-9])(?:{pattern})(?![A-Z0-9])", text) is not None


def _first(text: str, choices, default: str = "") -> str:
    return next((label for label, pattern in choices if _has(text, pattern)), default)


def describe(title: str) -> ReleaseInfo:
    upper = title.upper()
    tech = TECH.search(upper)
    end = tech.start() if tech else len(title)
    # « Blade.Runner.2049.2017 » : l'année est la dernière avant les tags
    years = [m for m in YEAR.finditer(title) if 0 < m.start() < end]
    year = years[-1] if years else None
    season = SEASON.search(upper)
    cut = min([m.start() for m in (year, season) if m] + [end])
    hdr = [label for label, pattern in HDR if _has(upper, pattern)]
    if "HDR10+" in hdr and "HDR" in hdr:
        hdr.remove("HDR")
    return ReleaseInfo(
        name=re.sub(r"[._]+", " ", title[:cut]).strip(" -([") or title,
        year=year.group() if year else "",
        season=season.group() if season else "",
        resolution=_first(upper, RESOLUTIONS, "SD"),
        langs=tuple(lang for lang in LANGS if _has(upper, lang)),
        source=_first(upper, SOURCES, "Autre"),
        hdr=tuple(hdr),
        codec=_first(upper, CODECS),
    )
