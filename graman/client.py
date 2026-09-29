"""Graman 클라이언트 — 게시물 목록/메타데이터/다운로드 (curl_cffi, 브라우저 없음)"""
import  asyncio
import  json

from curl_cffi.requests import AsyncSession

from .assets import ensure_assets
from .config import DOMAINS, IMPERSONATE, UA
from .models import Endpoint, MediaKind, Post, UserProfile
from .signer import Signer


class Graman:
    """여러 미러 도메인을 순서대로 시도하는 Instagram 수집 클라이언트."""

    def __init__(self, domains: list[str] | None = None):
        self.domains = domains or DOMAINS
        self.sessions: dict[str, AsyncSession] = {}
        self.signers: dict[str, Signer] = {}
        self._sem = asyncio.Semaphore(6)

    def _session(self, domain: str) -> AsyncSession:
        if domain not in self.sessions:
            self.sessions[domain] = AsyncSession(impersonate=IMPERSONATE)
        return self.sessions[domain]

    async def _post_api(self, domain: str, endpoint: Endpoint, payload: dict) -> dict:
        async with self._sem:
            s = self._session(domain)
            signer = self.signers.get(domain)
            if signer is None:
                adir = await ensure_assets(domain, s)
                signer = self.signers[domain] = Signer(domain, adir)
            res = await signer.mint(payload)
            if not res.get("ok"):
                raise RuntimeError(f"[{domain}] mint 실패: {res.get('error')}")
            r = await s.post(
                f"https://api-wh.{domain}{endpoint.value}",
                json=res["signed"],
                headers={"user-agent": UA, "origin": f"https://{domain}",
                         "referer": f"https://{domain}/", "accept": "application/json"},
                impersonate=IMPERSONATE, timeout=30,
            )
            # r.text의 자동 인코딩 판정은 한글 프로필 이름을 깨뜨릴 수 있다.
            return json.loads(r.content)

    async def posts(self, username: str):
        """마지막 커서까지 모든 게시물과 메타데이터를 생성한다."""
        cur = ""
        while True:
            data = None
            for d in self.domains:
                try:
                    j = await self._post_api(d, Endpoint.POSTS_V2, {"username": username, "maxId": cur})
                    data = j.get("result") or (j.get("data") or {}).get("result")
                    if data and data.get("edges"):
                        break
                except Exception:
                    continue
            if not data or not data.get("edges"):
                return
            for edge in data["edges"]:
                yield Post.from_raw(edge.get("node", {}))
            pi = data.get("page_info") or {}
            if not pi.get("has_next_page"):
                return
            next_cur = pi.get("end_cursor", "")
            if not next_cur or next_cur == cur:
                return
            cur = next_cur

    async def convert(self, ig_url: str) -> dict:
        """단건 미디어 해석 (다운로드 URL)"""
        for d in self.domains:
            try:
                return await self._post_api(d, Endpoint.CONVERT, {"target_url": ig_url})
            except Exception:
                continue
        return {}

    async def user_info(self, username: str) -> UserProfile | None:
        """소개, 팔로워/팔로잉, 게시물 수 등 계정 정보를 반환한다."""
        for d in self.domains:
            try:
                raw = await self._post_api(d, Endpoint.USER_INFO, {"username": username})
                profile = UserProfile.from_raw(raw)
                if profile.username:
                    return profile
            except Exception:
                continue
        return None

    async def download(self, url: str, dest: str, kind: MediaKind = MediaKind.IMAGE):
        from urllib.parse import urlparse
        s = self._session(urlparse(url).hostname or self.domains[0])
        r = await s.get(url, headers={"user-agent": UA, "referer": "https://www.instagram.com/"},
                        impersonate=IMPERSONATE, timeout=120)
        with open(dest, "wb") as f:
            f.write(r.content)
        return dest

    async def close(self):
        for sg in self.signers.values():
            await sg.close()
        for s in self.sessions.values():
            await s.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        await self.close()
