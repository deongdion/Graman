"""도메인별 app.js + link.chunk.js 자동 수집"""
import re
from pathlib import Path

from curl_cffi.requests import AsyncSession

from .config import ASSETS_DIR, UA


async def ensure_assets(domain: str, session: AsyncSession) -> Path:
    """domain의 (app.js, link.chunk.js)를 캐시(ASSETS_DIR/{domain}/)에 확보해 디렉터리 반환"""
    d = ASSETS_DIR / domain
    d.mkdir(parents=True, exist_ok=True)
    app_path = d / "app.js"
    chunk_path = d / "link.chunk.js"
    if app_path.exists() and chunk_path.exists():
        return d

    base = f"https://{domain}"
    r = await session.get(base + "/en/", headers={"user-agent": UA}, impersonate="chrome131")
    html = r.text
    app_src = next((m for m in re.findall(r'<script[^>]+src="([^"]+)"', html) if "app.js?id=" in m), None)
    if not app_src:
        raise RuntimeError(f"[{domain}] app.js not found")
    app_url = app_src if app_src.startswith("http") else base + app_src

    rj = await session.get(app_url, headers={"user-agent": UA}, impersonate="chrome131")
    js = rj.text
    # link.chunk ID는 사이트마다 다름 (54, 909 …)
    m = re.search(r'\.u=e=>"js/"\+\((\d+)===e\?"link\.chunk":e\)\+"\.js\?ch="\+\{([^}]*)\}', js)
    h = m and re.search(rf'(?:^|,){m.group(1)}:"([0-9a-f]+)"', m.group(2))
    if not h:
        raise RuntimeError(f"[{domain}] chunk map not found")
    chunk_url = f"{base}/js/link.chunk.js?ch={h.group(1)}.js"

    rc = await session.get(chunk_url, headers={"user-agent": UA}, impersonate="chrome131")
    app_path.write_text(js, encoding="utf-8")
    chunk_path.write_text(rc.text, encoding="utf-8")
    return d
