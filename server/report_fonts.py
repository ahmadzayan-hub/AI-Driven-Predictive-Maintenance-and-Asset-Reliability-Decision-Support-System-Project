"""Optional verified presentation resource; never changes approved report data."""
from hashlib import sha256
from pathlib import Path

FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "Dubai-Regular.ttf"
FONT_SHA256 = "e7b232e0d3a6699f9d9023c0b49a9288ead97a33bc5175b9d1619c09f8672298"
FONT_KEY = "{E7B232E0-D3A6-499F-9D90-23C0B49A9288}"


def verified_font():
    try:
        with FONT_PATH.open("rb") as stream:
            data = stream.read(139929)
    except OSError:
        return None
    return data if len(data) == 139928 and sha256(data).hexdigest() == FONT_SHA256 else None


def font_readiness():
    available = verified_font() is not None
    return {"family": "Dubai" if available else "Arial", "dubai_available": available,
            "embedded": available, "formats": ["html", "docx"], "pdf": False}


def obfuscate_font(data):
    """Reversible OOXML font packaging, not subsetting or font modification."""
    key = bytes.fromhex(FONT_KEY.strip("{}").replace("-", ""))[::-1]
    return bytes(value ^ key[index % 16] for index, value in enumerate(data[:32])) + data[32:]
