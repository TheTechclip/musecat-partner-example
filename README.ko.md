# Musecat Partner Example

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md)
유효한 앱 등록은 개발 모드에서 소유자와 지정 테스트 계정 최대 10명이 즉시 사용할 수 있습니다. 일반 사용자 대상 실서비스 전환에는 운영자 승인이 필요합니다. 자격증명과 사용자 동의는 두 모드 모두 필요합니다. B 전용 등록은 다섯 게임을 선언하며 기존 양방향 예제는 츄니즘 manifest를 유지합니다. [게임별 규격·최근 플레이·선택 항목·캐시 무효화](docs/record-adapters.md).


A runnable OAuth/OIDC example for Musecat Preview: PKCE, synthetic
CHUNITHM records, joint consent, standalone login, and bilateral revocation. Python + Flask + SQLite,
with Docker Compose and optional Caddy HTTPS. MIT licensed.

뮤즈캣 외부 연동을 직접 구현해 보는 **개발·테스트용 샘플**입니다. `alice` / `bob` 두 데모
계정과 가상 전적을 사용합니다. 실제 게임 계정 수집이나 상용 OAuth 서버 운영을 위한 제품은 아닙니다.

[localhost 및 실제 preview 연결 실행 안내](docs/local-development.md)

## 확인할 수 있는 흐름

- **OIDC 로그인**: 뮤즈캣 로그인 → ID token·UserInfo 검증 → 별도 로컬 세션 → 근처 오락실 조회
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

샘플은 일반 기능 위임 scope `account:access`와 `/developer/v1/account/*`, `/developer/v1/me` API를 사용합니다.
별도의 OIDC 로그인은 독립 앱과 자격증명으로 `openid profile arcade:read`를 요청하며, `account:access`를 부여하지 않습니다.

## 먼저 연결 목적을 선택하세요

아래 방향은 **데이터 접근 방향**이며 어느 사이트에서 시작하는지와 다릅니다.

| 목적 | 시작 위치 | 등록 JSON | 예제에 필요한 뮤즈캣 발급 시크릿 |
| --- | --- | --- | --- |
| 뮤즈캣 계정으로 로그인 | 홈 → **뮤즈캣으로 로그인** | `/onboarding.json?flow=login` | 별도 `MUSECAT_LOGIN_CLIENT_SECRET`, ID는 `MUSECAT_LOGIN_CLIENT_ID` |
| 예제에서 뮤즈캣 프로필/API 조회 (A만) | 데모 로그인 → **뮤즈캣 정보만 연결** | `/onboarding.json?flow=a` | `MUSECAT_CLIENT_SECRET` |
| 뮤즈캣에서 예제 전적 조회 (B만) | 뮤즈캣 설정 → 일반 외부 계정 연결 → 예제의 CHUNITHM 선택 → 연결 | `/onboarding.json?flow=b` | 없음. 생성된 파트너 OAuth ID/시크릿을 뮤즈캣에 설정 |
| 통합 동의로 양방향 연결 | 어느 서비스에서든 **원클릭 양방향 연결** | `/onboarding.json?flow=joint` (기본값) | `MUSECAT_CLIENT_SECRET`, `PARTNER_TO_MUSECAT_KEY`. 생성된 파트너 OAuth 정보와 `MUSECAT_TO_PARTNER_KEY`도 뮤즈캣에 전달 |

모든 모드는 로컬 세션·암호화·데모 계정용 생성 값을 사용합니다. 사용하지 않는 모드의 생성 키는 `.env`에 두어도 되며 교환할 필요가 없습니다. 앱 등록과 정확한 콜백 등록은 공통입니다. **B 전용 앱을 등록할 수 있습니다.** `/onboarding.json?flow=b`는 `direction_a`를 완전히 생략합니다. 개발자 센터에서 A를 끄고 B만 선언하면 A 콜백·뮤즈캣 발급 A 시크릿·Joint 키가 필요하지 않습니다. 이미 전체 기능으로 등록된 앱은 등록 변경 없이 세 버튼을 독립적으로 시험할 수 있습니다. 모드를 바꿀 때마다 세 JSON을 번갈아 제출하지 마세요. 등록된 설정을 변경하면 기존 동의가 무효화될 수 있습니다.

A의 성공 기준은 예제에 **단방향 뮤즈캣 API 연결**이 표시되고 공개 프로필을 조회하는 것입니다. `account:access`에는 문서화된 일반 사용자 쓰기 기능도 포함되며 읽기 전용 scope나 OIDC 로그인이 아닙니다. B는 뮤즈캣에 계정이 연결되고 가상 전적을 조회하면 성공입니다. **프로필 공개는 별도로 켜고** 공개 프로필에서 확인하세요. 예제의 동의 건수는 토큰 교환을 마친 접근 권한이며, 뮤즈캣의 캐시·실제 프로필 표시 상태를 증명하지는 않습니다. B만 연결한 계정의 해제는 뮤즈캣 설정에서 합니다. A만 해제해도 별도로 만든 B 권한은 유지됩니다. 독립 동의 두 개가 자동으로 공동 연결이 되지는 않습니다.

Alice의 데모를 유지하며 다른 모드를 시험하려면 `bob`을 사용하세요. 다만 뮤즈캣의 계정 중복 연결 규칙은 그대로 적용되므로 같은 뮤즈캣 계정을 충돌하는 데모 계정에 승인하지 마세요. 계정 변경은 기존 연결을 의도적으로 해제한 뒤 진행하세요. 별도의 **뮤즈캣으로 로그인**은 아래 절차로 구현되어 있습니다. Alice의 등록된 A/B/Joint 앱을 수정하지 말고 로그인 앱을 따로 등록하세요. 설정 변경 승인으로 기존 grant가 무효화될 수 있습니다.

### 첫 연결이 실패할 때

| 증상 | 확인 및 복구 |
| --- | --- |
| A 버튼이 비활성화됨 | 등록된 앱의 Client Secret을 `MUSECAT_CLIENT_SECRET`에 설정. 양방향 키 교환은 불필요 |
| 뮤즈캣에 제공자가 없음 | 개발자 센터의 앱 등록, 등록된 B 선언, 파트너 OAuth credential 확인 |
| `invalid_origin` | 정확한 HTTPS `PARTNER_ORIGIN`으로 접속. 터널 변경 시 origin·승인 URL을 바꾸고 컨테이너 재생성 |
| `invalid_client` 또는 콜백 거부 | 키 발급 주체와 방향, 등록한 콜백의 정확한 일치 확인 |
| `invalid_grant`·잘못된 state·만료 | 같은 브라우저 세션에서 새로 시작. 콜백·코드 재사용 금지. refresh 소모 후에는 재연결 |
| `records_private` 또는 프로필에 전적 없음 | 예제 공개 상태, 뮤즈캣 서비스 공개 스위치, 캐시 상태·새로고침 제한 확인 |
| HTTP 429 | 해당 API의 재시도 시간을 준수. 모든 예제를 자동 반복 실행하지 않기 |


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
issuer와 콜백도 바뀌므로 기존 앱에 URL을 변경·등록 갱신하고 연결을 새로 만들어야 합니다.
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
2. 뮤즈캣 개발자 센터에서 선택한 흐름의 JSON으로 앱을 등록합니다. 기본 정보와 해당 JSON에 포함된 방향만 입력합니다.
   `contact_email`은 본인 연락처로 변경하세요.
3. 유효한 등록은 개발 모드에서 즉시 사용할 수 있습니다. 소유자 외 계정은 테스트 사용자로 지정하세요. 일반 사용자 공개는 별도 승인이 필요합니다.
4. 아래 자격증명을 교환합니다. 값은 **서버 전용**이며 GitHub 이슈·스크린샷·브라우저 JS에 넣지 않습니다.

| 값 | 발급 주체 | 설정 위치 |
| --- | --- | --- |
| Client ID | 뮤즈캣 (`PARTNER_ID`와 같음) | 샘플 `.env`의 `PARTNER_ID` |
| Client Secret | 뮤즈캣, 최초 발급/재발급 순간에 표시 | `.env`의 `MUSECAT_CLIENT_SECRET` |
| 별도 OIDC Client ID / Secret | 뮤즈캣의 별도 로그인 앱 | `.env`의 `MUSECAT_LOGIN_CLIENT_ID` / `MUSECAT_LOGIN_CLIENT_SECRET` |
| 파트너 OAuth Client ID / Secret | 샘플 초기화 스크립트 | 뮤즈캣 앱의 Direction B credential에 `PARTNER_OAUTH_CLIENT_ID` / `PARTNER_OAUTH_CLIENT_SECRET` 입력 |
| 뮤즈캣 → 샘플 joint key | 샘플 초기화 스크립트 | 뮤즈캣 앱의 **파트너 발급 Joint 키**에 `MUSECAT_TO_PARTNER_KEY` 입력 |
| 샘플 → 뮤즈캣 partner key | 뮤즈캣, 발급 순간에 표시 | `.env`의 `PARTNER_TO_MUSECAT_KEY` |

등록되는 주소는 다음과 같습니다. `<origin>`은 샘플의 HTTPS origin입니다.

| 용도 | 주소 |
| --- | --- |
| OIDC: 샘플이 받는 로그인 콜백 | `<origin>/oidc/callback` |
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

## 2.1. 별도의 뮤즈캣으로 로그인 (OIDC)

1. `python3 scripts/init-env.py`를 다시 실행해 기존 값을 유지하며 빠진 설정을 추가합니다. `MUSECAT_LOGIN_CLIENT_ID`의 기본값은 `PARTNER_ID + "_login"`이며 ID 길이 제한에 맞춰 앞부분을 자릅니다. 기존 A/B/Joint 앱과 자격증명은 유지합니다.
2. `/onboarding.json?flow=login`으로 **별도 앱**을 개발자 센터에 등록합니다. 앱 ID는 `MUSECAT_LOGIN_CLIENT_ID`와 일치해야 합니다. A와 `direction_a.login_enabled: true`를 켜고 콜백을 정확히 `<PARTNER_ORIGIN>/oidc/callback`으로 등록합니다. 이 양식에는 B·Joint가 없습니다. 연락처 등을 실제 정보로 바꾸고 등록을 저장하세요. 개발 테스트에는 운영자 심사가 필요하지 않습니다. 일반 공개에는 실서비스 심사를 요청하세요.
3. 등록 후 로그인 앱의 Client Secret을 발급받아 `.env`의 `MUSECAT_LOGIN_CLIENT_SECRET`에 입력하고 `docker compose up -d --build --force-recreate`로 재생성합니다. 기존 A/B/Joint 앱의 시크릿을 넣지 마세요.
4. 정확한 공개 HTTPS origin의 홈에서 **뮤즈캣으로 로그인**을 선택합니다. 데모 로그인이 필요하지 않습니다. 뮤즈캣에서 로그인하고 `openid profile arcade:read`에 동의하면 검증된 계정으로 로컬 세션을 만듭니다. 기존 데모 로그인 세션은 교체되지만 저장된 A/B/Joint grant를 합치거나 해제하지 않습니다.
5. 로그인한 홈의 근처 오락실 조회(`POST /oidc/nearby`)를 실행합니다. 서울 중심 반경 5 km의 고정된 읽기 요청이며 기기 위치를 수집하거나 오락실 전체 목록을 내보내지 않습니다. 이 로그인으로 `account:access` API 콘솔이나 데모 전적 도구의 권한이 생기지는 않습니다.
6. **로그아웃**(`POST /logout`)하면 로컬 접근을 즉시 끝내고 worker가 암호화된 영속 outbox로 토큰 회수를 재시도합니다. 뮤즈캣 전체 로그아웃이나 Alice의 별도 A/B/Joint 연결 해제는 아닙니다. 회수 대기가 끝날 때까지 worker를 실행하세요.

콜백은 PKCE S256·세션에 묶인 state·nonce를 사용합니다. 설정한 issuer의 JWKS로 RS256 ID token의 `kid`·서명·issuer·audience·발급 시각·만료·nonce를 검증하고 UserInfo의 `sub`도 일치해야 합니다. 로컬 ID는 issuer와 `sub`의 해시이며 닉네임·이메일로 `alice`/`bob`에 자동 병합하지 않습니다. 토큰은 서버에 암호화해 보관합니다. 로그인은 최대 10분이며 토큰 만료보다 길어지지 않습니다. 자동 refresh는 없으므로 만료되면 다시 로그인하세요. [구현](partner/oidc.py), [PyJWT 검증 API](https://pyjwt.readthedocs.io/en/stable/api.html)를 참고하세요.

### 오류별 복구

브라우저 화면에는 번역된 원인·다음 행동과 기존 오류 코드·HTTP 상태를 표시합니다. `invalid_origin`은 정확한 HTTPS origin, 설정·클라이언트 오류는 해당 앱과 자격증명, state·nonce·토큰 검증 오류는 새 로그인, 동의 거부는 사용자가 선택하는 재시도, 호출 제한은 대기 시간을 안내합니다. 콜백·인가 코드를 재사용하지 마세요. 원격 장애는 issuer·접속 가능 여부를 확인한 뒤 새 흐름을 시작합니다. 프로토콜/API 엔드포인트는 HTML 요청에도 JSON을 유지하며 브라우저 경로도 `?format=json`으로 진단할 수 있습니다. 알려진 원격 OAuth 오류 코드와 안전한 `Retry-After`만 전달하며 토큰·원격 응답 원문을 노출하지 않습니다. [오류 처리](partner/recovery.py)를 참고하세요.

위 내용은 구현된 절차입니다. Preview의 실제 OIDC 콜백 성공은 배포 후 별도로 기록해야 하며, 기존 A/B/Joint 검증 결과로 대체하지 않습니다.

## 3. 실제 테스트 순서

테스트용 뮤즈캣 개발 계정을 사용합니다. 두 데모 계정은 동일한 데모 비밀번호를 공유하므로
공개 배포에서는 등록된 테스트 참여자에게만 비밀번호를 전달하세요.

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
| `partner/oidc.py` | 독립 OIDC 로그인·검증된 계정/세션·근처 조회·로그아웃 회수 |
| `partner/recovery.py` | 다국어 브라우저 복구 안내·프로토콜 JSON 오류 유지 |
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

## 츄니즘 화면용 전적 항목

가상 응답에는 `rating`, `rating_max`, `over_power`, `played_chart_count`, `full_combo_count`, `all_justice_count`, `last_played_at`, `last_synced_at`이 들어 있습니다. `rank_distribution` 섹션은 `rank` 열(타입 `rank`)과 `count` 열(타입 `integer`)을 제공합니다. Musecat은 이 선택적 키를 츄니즘 레이팅·달성률·랭크 UI로 변환할 수 있습니다. `played_chart_count`는 서로 다른 플레이한 보면 수이며 플레이 횟수가 아닙니다. 알 수 없는 값은 0으로 채우지 않고 생략합니다. 전송 규격은 계속 `musecat-records/v1`이며 별도의 싱크 API를 만들지 않습니다. 출처에는 가상 데이터임을 명시합니다.

## 개발자 API 전체 예제

데모 로그인 후 `/api-examples`의 **개발자 API 예제**를 엽니다. 공식 Developer OpenAPI의 **92개 경로·104개 작업**과 문서에 정의된 모든 요청 형식을 제공합니다. 각 항목에서 파라미터·필요 권한·수정 가능한 요청 필드·생성된 응답 예제·원본 응답 규격·환경변수 자리표시자를 사용하는 curl 명령을 확인합니다. 스냅샷에는 앱 인증정보나 테스트 계정 데이터가 없습니다.

계정 API는 현재 암호화된 연결과 토큰 회전 로직을 사용해 서버에서 호출합니다. 브라우저에는 응답만 전달하고 access/refresh token을 보내지 않습니다. 오류 HTTP 상태와 응답 본문도 표시하며, 파일 업로드는 명세의 multipart 필드를 지원합니다. 변경 요청은 해당 HTTP 메서드를 직접 입력해야 실행되고 전체 변경 API를 자동으로 실행하지 않습니다.

OAuth·뮤즈캣 로그인 세션용 9개 작업은 참고 예제로 제공합니다. 인가·동의는 정상 브라우저 흐름, 클라이언트 인증은 서버 인증정보, 승인 관리는 뮤즈캣 세션을 사용해야 합니다. 실제 A/B/공동 연결 흐름은 `partner/client.py`, `partner/oauth.py`, `partner/joint.py`에 있습니다. OIDC 권한은 별도로 활성화된 앱이 필요하며 `account:access` 토큰의 권한을 임의로 확대하지 않습니다.

**뮤즈캣 프로필 조회**는 기존 계정 API로 전체 프로필(게임·즐겨찾기·국가·SNS·레벨·관리 오락실 등 반환되는 필드), 패스포트 집계, 스탬프 첫 페이지, 활동, 기여 기록 첫 페이지를 함께 읽습니다. 다음 페이지와 필터는 API 콘솔에서 실행합니다. 일반 제3자에게 공개된 정보만 조회하며, 조회 결과는 공개 가상 전적에 복사하지 않습니다. 폼 필드 `format=json`을 추가하면 종합 JSON 응답을 받습니다.

```sh
python examples/list_examples.py
python examples/list_examples.py --operation 'GET /developer/v1/account/user/me'
# 검토용 출력입니다. 파일 전체를 일괄 실행하지 마세요.
python examples/list_examples.py --all > /tmp/musecat-api-examples.sh
```

`partner/developer-openapi.json`은 Backend Core `80568ba0cba2758a8f539207476d2b9e5fd93918`의 공식 계약 스냅샷이며 `/api-examples/openapi.json`에서도 제공합니다. 배포 명세로 갱신하려면 다음을 실행합니다. YAML 변환은 개발 작업이며 실행 서버의 추가 의존성이 아닙니다.

```sh
.venv/bin/pip install -r requirements-dev.txt
curl --fail --silent --show-error https://db-dev.musecat.app/developer/openapi.yaml -o /tmp/musecat-developer-openapi.yaml
.venv/bin/python scripts/update-api-schema.py /tmp/musecat-developer-openapi.yaml
.venv/bin/python -m unittest discover -v
```

테스트는 전체 작업·요청 형식 포함 여부, 고정 origin 호출, 서버 토큰 처리, 변경 확인, HTTP 오류 표시, 전체 프로필 구성, 조회 중 연결 해제를 검증합니다. 뮤즈캣의 기존 검증·역할·공개 범위·GPS 조건·호출 제한도 그대로 적용됩니다.

[개발자 API 검증 결과](docs/developer-api-test-results.md)

외부 앱의 프로필 조회는 일반 제3자와 같은 공개 규칙을 따릅니다. 비공개 즐겨찾기·게임은 제외되며, 국가는 프로필 공개 설정을 따릅니다. 비공개 패스포트는 조회할 수 없고 요약 공개 시 방문 날짜가 제외됩니다. 오락실 전체 목록 API는 외부에 제공하지 않으며 개별 조회와 주변 검색은 지원합니다.

처음 접하는 개발자 기준의 부족점과 남은 플랫폼 과제는 [온보딩 검토](docs/onboarding-review.ko.md)를 참고하세요.

게임·제공자별 원본 규격은 어댑터가 공통 봉투로 변환합니다. 게임별 지표 의미와 전용 시각화까지 자동 통일되는 것은 아닙니다. [어댑터 규약과 한계](docs/record-adapters.md), 사볼 가상 변환 예제를 참고하세요.
