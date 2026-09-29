# Graman

Instagram 프로필 정보 + 전체 게시물 목록/캡션/좋아요/댓글/조회수/미디어URL 수집기.
**curl_cffi + Node 서명기만 사용 — 브라우저 없음.**

## 동작 구조

- gramsnap 계열(gramsnap/fastdl/sssinstagram/igram)은 동일 백엔드이며
  `api-wh.{domain}/api/v1/instagram/postsV2` 가 목록+메타데이터를 줌 (12개/페이지, end_cursor 페이지네이션).
  - posts 엔드포인트는 convert(다운로드) 리밋 버킷과 **분리**되어 목록 수집은 사실상 무제한 (실측).
  - convert는 도메인당 ~20 req/min, 60s 쿨다운 → 미러 도메인을 순서대로 시도.
- 요청 바디는 `{username, maxId}` + 서명(`ts,_ts,_tsc,_s`)이 필수인데, 서명은
  원본 `link.chunk.js`를 **Node에서 직접 실행**하는 `graman/js/minter.js`가 생성 (브라우저 불필요).
  - 도메인마다 서명 키가 달라서(교차 시 401 HASH_MISMATCH 실측) 도메인별로 자산을 자동 수집해 민팅.
- `userInfo`에서 소개, 팔로워/팔로잉, 게시물 수, 프로필 사진, 외부 링크, 공개/인증 여부를 수집.
- 프록시는 사용하지 않으며 모든 요청은 현재 네트워크에서 직접 전송.
- 게시물은 페이지 수 제한 없이 `has_next_page`가 끝날 때까지 전부 수집.

## 설치

```
pip install -r requirements.txt   # curl_cffi
```
Node.js 필요 (https://nodejs.org 또는 기존 설치). `node -v`로 확인.

## 사용

`.env` 없음 — 설정은 코드 인자로 넘김.

1. `example.py` 상단 상수 수정: `USERNAME`, `TARGET_URL`
2. 실행
```
python selftest.py   # 민팅 + postsV2 1회 검증 (가장 먼저)
python example.py    # 목록 수집 → 콘솔 출력 (게시물별 + 요약)
```

라이브러리로 쓸 때:
```python
from graman import Graman

async with Graman() as g:
    profile = await g.user_info("instagram")
    print(profile.followers, profile.following, profile.biography)

    async for post in g.posts("instagram"):  # 마지막 페이지까지 전부
        print(post.shortcode, post.likes)
```

## 서명 게이트 (중요)

`minter.js`는 원본 청크를 오프라인 실행하는데, 서명기 초기화에 **안티탬퍼 게이트** 1개가 있음.
내 개발 샌드박스는 외부 네트워크가 차단되어 게이트 통과 여부를 끝까지 검증하지 못함.

- `python selftest.py` 결과가 `성공!`이면 바로 사용 가능.
- `Cant-create-signed-request-body`로 실패하면:
  1) `graman/config.py`의 `GM_ONLINE`을 `True` ↔ `False` 바꿔 재시도 (geo 페치 실네트워크/스텁 토글)
  2) 그래도 안 되면 게이트 RE가 필요 — `graman/js/minter.js`의 부트 구조는 완성돼 있으므로
     게이트 조건(j3JAfg/oTlhbB/SgvaoFr 변수들)만 추가 패치하면 됨.

## 파일

| 경로 | 역할 |
|---|---|
| `graman/client.py` | postsV2 전체 페이지네이션, 프로필, convert, 다운로드, 도메인 폴백 |
| `graman/signer.py` | node minter 상주 프로세스 (stdin/stdout JSON 라인) |
| `graman/assets.py` | 도메인별 app.js + link.chunk.js 자동 수집 → 캐시 (`%LOCALAPPDATA%\graman\assets`, `~/.cache/graman/assets`, `GRAMAN_CACHE_DIR`로 변경) |
| `graman/js/minter.js` | 원본 청크 오프라인 실행 서명기 (webpack 셔빙 + 폴리필) |
| `selftest.py` | 민팅 + API 1회 검증 |

## 리밋 참고 (2026-09-29 실측)

| 도메인 | convert 리밋 | 쿨다운 | posts |
|---|---|---|---|
| sssinstagram.com | ~20 burst | 60s | 별도 버킷, 사실상 무제한 |
| fastdl.app | ~15 burst | 60s | 〃 |
| igram.world | ~18 burst | 60s | 〃 |
| gramsnap.com | 3/10s + 캡차 | - | 사용 비권장 |
