# Musecat Partner Example

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

A runnable, single-client OAuth partner for Musecat Preview: PKCE, synthetic
CHUNITHM records, joint consent, and bilateral revocation. Python + Flask + SQLite,
with Docker Compose and optional Caddy HTTPS. MIT licensed.

뮤즈캣 외부 연동을 직접 구현해 보는 **개발·테스트용 샘플**입니다. `alice` / `bob` 두 데모
계정과 가상 전적을 사용합니다. 실제 게임 계정 수집이나 상용 OAuth 서버 운영을 위한 제품은 아닙니다.

## 확인할 수 있는 흐름

- **A**: 샘플 → 뮤즈캣 동의 → 프로필 조회 → refresh 회전 → 해제
- **B**: 뮤즈캣 → 샘플 동의 → 가상 전적 조회 → 공개/비공개 → refresh 복구
- **Joint**: 양쪽 어느 곳에서 시작해도 뮤즈캣 공동 동의 한 번으로 양쪽 권한 발급
- 양쪽 교환 및 뮤즈캣 상태 확인 후에만 완료 표시, 불완전한 연결은 부분 연결로 표시
- 양쪽에서 해제, 세대가 다른 해제 요청 격리, 재연결, 영속 outbox 재시도

고정 개발 환경:

| 항목 | 주소 |
| --- | --- |
| Musecat API / OAuth issuer | `https://db-dev.musecat.app` |
| 웹 / 개발자 센터 | <https://preview.musecat.app/kr/developer> |
| 최신 연동 계약 | <https://preview.musecat.app/api/developer/spec> |

샘플은 일반 기능 위임 scope `account:access`를 사용하고 `/developer/v1/me`만 호출합니다.
`openid profile arcade:read` 로그인 전용 예제와는 구분됩니다.

## 1. 로컬 실행 준비

Docker Compose, Python 3, 공개 HTTPS 주소가 필요합니다. Musecat은 파트너 서버를 직접
호출하므로 `localhost` 주소만으로는 등록할 수 없습니다.

```sh
git clone https://github.com/TheTechclip/musecat-partner-example.git
cd musecat-partner-example
python3 scripts/init-env.py
```

`.env`에는 무작위 데모 비밀번호·세션 키·암호화 키·파트너 발급 키가 생성됩니다.
기존 값을 덮어쓰지 않습니다. `.env`는 Git과 Docker 빌드 컨텍스트에서 제외됩니다.

### 선택 A: 로컬 + 임시 HTTPS 터널

별도 터미널에서 [Cloudflare Quick Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)을 실행합니다.

```sh
cloudflared tunnel --url http://127.0.0.1:8088 --no-autoupdate
```

출력된 `https://...trycloudflare.com`을 `.env`의 `PARTNER_ORIGIN`에 설정하고,
`PARTNER_HOST`에는 호스트 이름만 설정합니다. 마지막 `/`는 넣지 않습니다.

```sh
docker compose up -d --build
docker compose ps
```

**브라우저도 HTTPS 터널 주소로 접속**하세요. 쿠키는 Secure입니다. 터널 주소가 바뀌면
issuer와 콜백도 바뀌므로 기존 앱에 URL을 변경·재승인하고 연결을 새로 만들어야 합니다.
Quick Tunnel은 임시 테스트용입니다. 주소를 고정하려면 named tunnel이나 아래 방식을 사용하세요.

### 선택 B: 고정 도메인 + Caddy

도메인의 DNS를 실행할 서버로 연결하고 80/443 포트를 열어 둡니다. `.env`의
`PARTNER_ORIGIN=https://your-domain.example`, `PARTNER_HOST=your-domain.example`을 설정합니다.

```sh
docker compose --profile https up -d --build
```

이미 HTTPS 프록시가 있다면 Caddy 없이 `app:8080`으로 연결하면 됩니다.

### 화면 언어

예제 화면은 영어·한국어·일본어를 지원합니다. 상단에서 언어를 선택하고 **변경**을 누르면 로그인·로그아웃 후에도 유지됩니다. 처음에는 브라우저 언어를 사용하며 일치하지 않으면 영어로 표시합니다. 로그인·동의·연결·테스트 도구를 번역하고 프로토콜 식별자와 JSON 오류 코드는 그대로 유지합니다. 샘플에서 시작한 공동 동의에는 선택한 언어를 적용하며 Musecat에서 시작한 흐름은 Musecat이 지정한 언어를 유지합니다.

## 2. 뮤즈캣 개발자 센터 등록

샘플은 Musecat 키가 없어도 시작됩니다. `.env`의 `DEMO_PASSWORD`로 샘플에 로그인하세요.

1. 샘플의 **앱 등록 JSON** (`/onboarding.json`)을 엽니다. 실제 URL과 생성된 `PARTNER_ID`가 들어 있습니다.
2. 뮤즈캣 개발자 센터에서 앱을 등록하고, JSON의 기본 정보·Direction A·B·Joint 설정을 입력합니다.
   `contact_email`은 본인 연락처로 변경하세요.
3. 등록 요청 후 뮤즈캣 운영자의 승인을 받습니다. 승인은 샘플에서 우회하지 않습니다.
4. 아래 자격증명을 교환합니다. 값은 **서버 전용**이며 GitHub 이슈·스크린샷·브라우저 JS에 넣지 않습니다.

| 값 | 발급 주체 | 설정 위치 |
| --- | --- | --- |
| Client ID | 뮤즈캣 (`PARTNER_ID`와 같음) | 샘플 `.env`의 `PARTNER_ID` |
| Client Secret | 뮤즈캣, 최초 발급/재발급 순간에 표시 | `.env`의 `MUSECAT_CLIENT_SECRET` |
| 파트너 OAuth Client ID / Secret | 샘플 초기화 스크립트 | 뮤즈캣 앱의 Direction B credential에 `PARTNER_OAUTH_CLIENT_ID` / `PARTNER_OAUTH_CLIENT_SECRET` 입력 |
| 뮤즈캣 → 샘플 joint key | 샘플 초기화 스크립트 | 뮤즈캣 앱의 **파트너 발급 Joint 키**에 `MUSECAT_TO_PARTNER_KEY` 입력 |
| 샘플 → 뮤즈캣 partner key | 뮤즈캣, 발급 순간에 표시 | `.env`의 `PARTNER_TO_MUSECAT_KEY` |

등록되는 주소는 다음과 같습니다. `<origin>`은 샘플의 HTTPS origin입니다.

| 용도 | 주소 |
| --- | --- |
| Direction A: 샘플이 받는 뮤즈캣 콜백 | `<origin>/oauth/musecat/callback` |
| Direction B: 뮤즈캣이 받는 샘플 콜백 | `https://preview.musecat.app/api/user/connections/callback/<PARTNER_ID>` |
| 샘플 OAuth | `/oauth/authorize`, `/oauth/token`, `/oauth/userinfo`, `/oauth/revoke` |
| 전적 | `<origin>/api/records/chunithm` |
| Joint base | `<origin>/api/joint` |
| 뮤즈캣 시작 시 파트너 진입점 | `<origin>/connect/musecat/start` |
| 공동 동의 화면 | `https://preview.musecat.app/kr/connect/<PARTNER_ID>` |

환경변수 변경 후:

```sh
docker compose up -d --build --force-recreate
```

`DATA_KEY`와 `SESSION_SECRET`은 재시작할 때 그대로 유지하세요. 암호화 키를 잃으면 기존 토큰과
outbox를 읽을 수 없습니다. 샘플은 현재 연결을 먼저 해제한 뒤 새 연결을 시작하도록 합니다.

## 3. 실제 테스트 순서

테스트용 뮤즈캣 개발 계정을 사용합니다. 두 데모 계정은 동일한 데모 비밀번호를 공유하므로
공개 배포에서는 승인된 테스트 참여자에게만 비밀번호를 전달하세요.

1. 샘플 로그인 → **일반 OAuth 연결만** → 뮤즈캣 동의 → 프로필 조회와 토큰 갱신 후 조회
2. 연결 해제 → worker가 알림을 전송하고 뮤즈캣 설정에서도 승인 해제 확인
3. 샘플에서 **원클릭 양방향 연결** → 두 계정과 권한 확인 → 한 번 동의 → 완료
4. 뮤즈캣 설정의 외부 연결에서 전적 조회. 샘플은 `musecat-records/v1`을 반환합니다.
5. 샘플 비공개 시 뮤즈캣은 `records_private`로 숨겨야 합니다. 공개 변경 후 새로고침은 분당 1회 제한을 따릅니다.
6. 뮤즈캣의 **프로필에 공개**도 켰을 때만 익명 프로필에 전적이 표시되는지 확인
7. 샘플의 **데모 access token 만료** → 1분 후 뮤즈캣 새로고침 → 자동 refresh 후 전적 복구
8. 샘플에서 양쪽 해제 → 뮤즈캣 승인과 외부 전적 연결이 모두 해제되는지 확인
9. 뮤즈캣 설정에서 양방향 연결 시작 → 샘플 로그인 → 공동 동의 → 완료 후 뮤즈캣 설정으로 복귀
10. 뮤즈캣에서 **공동 연결 해제** → 샘플에서도 해제 확인 → 새 연결로 재연결

일반 외부 계정 연결 삭제와 **공동 연결 해제**는 다릅니다. 양쪽 해제 확인에는 공동 연결 메뉴를 사용합니다.
해제 전송 대기 동안에는 로컬 접근이 즉시 차단되고, worker가 SQLite outbox를 재시도합니다.

실제 Preview와의 검증 범위는 [실측 결과](docs/preview-test-results.md)를 참고하세요.

## 구성과 검증

| 파일 | 역할 |
| --- | --- |
| `partner/oauth.py` | 파트너 OAuth 서버와 가상 전적 API |
| `partner/client.py` | 뮤즈캣 OAuth client와 실제 토큰 교환·갱신 |
| `partner/joint.py` | intent 조회·원자적 receipt·멱등·양방향 해제 수신 |
| `partner/storage.py` | Fernet 암호화 SQLite ledger |
| `partner/worker.py` | 영속 해제 전송 큐·지수 backoff·만료 데이터 정리 |
| `partner/i18n.py` | 영어·한국어·일본어 화면 문구 |
| `partner/web.py` | 데모 로그인·공개 설정·등록 양식·토큰 만료 테스트 도구 |

로컬 Python 테스트에는 Python 3.10 이상이 필요합니다. Docker 이미지는 Python 3.13을 사용합니다.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -v
docker compose config --quiet
```

테스트는 PKCE, 코드·refresh 재사용 거부, scope 격리, private 전적, 잘못된 콜백,
CSRF와 브라우저 Origin, 언어 선택, 잘못된 bearer, receipt 멱등·원자성, 세대 격리, 세션 교체, outbox 재시작을 다룹니다.
CI에서도 테스트와 Compose 검증 및 Docker 빌드를 실행합니다.

## 구현상 경계

- 단일 파트너 OAuth client와 두 데모 사용자에 한정합니다. 계정 가입·이메일·실제 게임 데이터는 없습니다.
- 비밀 원문은 환경변수에 있고, 서버에 저장되는 토큰·verifier·receipt 응답은 암호화합니다.
  token/intent/code의 조회 키는 SHA-256 해시입니다. 암호화 키는 DB와 함께 공개하지 않습니다.
- intent 5분, code 90초, access 10분, refresh family 30일. 사용한 refresh 재사용 시 grant를 회수합니다.
- Joint 요청은 별도 bearer와 `X-Request-Id` UUIDv4가 필요하며, 10분 동안 같은 요청 결과를 재사용합니다.
- 뮤즈캣 시작 시 `completion_uri`는 등록된 웹 origin의 해당 언어 설정 페이지만 허용합니다.
- outbox는 재시작 후에도 남고 24시간 이상 재시도합니다. 5초부터 최대 5분 간격으로 증가하며
  작업은 마지막 시도부터 1년 동안 보존합니다. 로컬 접근은 전송 결과와 관계없이 먼저 차단합니다.
- HTTP access log를 켜지 않습니다. OAuth 콜백과 intent URL을 로그·분석 도구에 수집하지 마세요.
- Joint 수신 키 교체 시 이전 키를 `MUSECAT_TO_PARTNER_PREVIOUS_KEY`, 24시간 후 Unix 초를
  `PREVIOUS_KEY_EXPIRES_AT`에 넣고 현재 키를 변경합니다. 이후 뮤즈캣의 파트너 발급 키를 갱신하고,
  유예 기간이 끝나면 이전 키 설정을 비웁니다.

이 샘플은 뮤즈캣 연동 학습용이며 OAuth/OIDC 제공자 전체 구현이 아닙니다.
규격의 정본은 위의 Musecat 연동 문서입니다. Flask와 cryptography 의존성 정보는 각각
[Flask PyPI](https://pypi.org/project/Flask/), [cryptography PyPI](https://pypi.org/project/cryptography/)를 참고하세요.
