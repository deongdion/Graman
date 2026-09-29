"""Graman 설정 — 상수 (.env 없음, 설정은 코드 인자로)"""
import os
from pathlib import Path

# 도메인 로테이션 순서 (gramsnap.com 제외: 리밋 최빡 + 캡차 에스컬레이션)
DOMAINS = ["sssinstagram.com", "fastdl.app", "igram.world"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
IMPERSONATE = "chrome131"

PKG_DIR = Path(__file__).resolve().parent
MINTER_JS = PKG_DIR / "js" / "minter.js"   # 패키지 데이터


def _cache_dir() -> Path:
    """런타임 다운로드 자산 캐시 — 패키지 밖(쓰기 가능 위치). GRAMAN_CACHE_DIR로 덮어쓰기 가능"""
    if os.environ.get("GRAMAN_CACHE_DIR"):
        return Path(os.environ["GRAMAN_CACHE_DIR"])
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "graman"


ASSETS_DIR = _cache_dir() / "assets"


GM_ONLINE = True  # minter가 geo 페치(/get_country_code)를 실네트워크로 시도 (False=로컬 스텁)
