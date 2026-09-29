"""minter.js 상주 프로세스 래퍼 — 브라우저 없이 서명 민팅"""
import asyncio
import json
import shutil

from .config import GM_ONLINE, MINTER_JS


class Signer:
    """node minter.js --serve 1개 프로세스를 도메인당 상시 구동, stdin/stdout JSON 라인 프로토콜"""

    def __init__(self, domain: str, assets_dir):
        self.domain = domain
        self.app = assets_dir / "app.js"
        self.chunk = assets_dir / "link.chunk.js"
        self.proc: asyncio.subprocess.Process | None = None
        self.lock = asyncio.Lock()
        self._id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._reader_task = None

    def _node_bin(self) -> str:
        for c in ("node", r"C:\Users\user\.aside\runtime\bin\node.cmd"):
            if shutil.which(c):
                return c
        raise RuntimeError("node 실행 파일 없음 — Node.js 설치 필요")

    async def start(self):
        if self.proc:
            return
        env = {"GM_ONLINE": "1" if GM_ONLINE else "0", "PATH": ""}
        import os
        env = {**os.environ, "GM_ONLINE": env["GM_ONLINE"], "GM_DOMAIN": self.domain}
        self.proc = await asyncio.create_subprocess_exec(
            self._node_bin(), str(MINTER_JS),
            str(self.app), str(self.chunk), "--serve",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, env=env,
        )
        # ready 핸드셰이크: {"ok":true,"ready":true}
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                err = await self.proc.stderr.read() if self.proc.stderr else b""
                raise RuntimeError(f"[{self.domain}] minter boot 실패: {err.decode(errors='ignore')[:300]}")
            j = json.loads(line)
            if j.get("ready"):
                break
            if j.get("ok") is False:
                raise RuntimeError(f"[{self.domain}] minter: {j.get('error')}")
        self._reader_task = asyncio.create_task(self._pump())

    async def _pump(self):
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            try:
                j = json.loads(line)
            except Exception:
                continue
            fut = self._pending.pop(j.get("id"), None)
            if fut and not fut.done():
                fut.set_result(j)

    async def mint(self, payload: dict) -> dict:
        async with self.lock:
            await self.start()
            self._id += 1
            rid = self._id
            fut = asyncio.get_running_loop().create_future()
            self._pending[rid] = fut
            self.proc.stdin.write((json.dumps({"id": rid, "payload": payload}) + "\n").encode())
            await self.proc.stdin.drain()
            return await asyncio.wait_for(fut, timeout=20)

    async def close(self):
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self.proc:
            if self.proc.returncode is None:
                try:
                    self.proc.kill()
                except ProcessLookupError:
                    pass
            try:
                await asyncio.wait_for(self.proc.wait(), timeout=5)
            except Exception:
                pass
            self.proc = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *a):
        await self.close()
