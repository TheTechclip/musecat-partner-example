> 현재 등록 정책: 유효한 개발 앱은 소유자와 지정 테스트 계정 10명까지 즉시 사용할 수 있습니다. 일반 사용자에게 공개하는 실서비스 전환에는 운영자 심사가 필요합니다. 자격증명 설정과 사용자 동의는 계속 필요합니다. localhost 및 실제 Preview 연결 절차는 [개발 안내](local-development.md)를 참고하세요. 게임별 최근 플레이·선택 항목·캐시 무효화는 [현재 규격](record-adapters.md)을 참고하세요.

# 신규 개발자 관점의 연동 온보딩 검토

갱신일: 2026-10-20 (Australia/Sydney)

공개 샘플의 세 언어 README, 등록 JSON, 환경변수 초기화, A/B/Joint·OIDC 구현, 오류 복구 화면 및 Musecat 등록 계약을 기준으로 정리했다. 아래 완료 표시는 **현재 소스 구현**에 관한 것이다. 개발서버 배포와 실제 OIDC 콜백 성공 여부는 별도의 실측 기록으로 확인해야 한다.

## 어떤 흐름을 선택해야 하는가

| 목적 | 흐름 | 최소 준비 |
| --- | --- | --- |
| 내 서버에서 사용자의 Musecat 일반 기능 호출 | A | `/onboarding.json?flow=a`, 등록, `MUSECAT_CLIENT_SECRET` |
| Musecat에 내 서비스 전적 제공 | B | `/onboarding.json?flow=b`, 등록, 파트너 OAuth 자격증명을 Musecat에 등록 |
| 두 방향을 공동 동의로 연결·해제 | Joint | 기본 `/onboarding.json` 또는 `?flow=joint`, 양쪽 OAuth 자격증명·Joint 키 교환 |
| Musecat 계정으로 내 서비스 로그인 | OIDC | 별도 `?flow=login` 앱 등록, `MUSECAT_LOGIN_CLIENT_ID`·`MUSECAT_LOGIN_CLIENT_SECRET` |

여기서 방향은 데이터 접근 방향이며 시작 사이트와 다르다. A와 B를 따로 연결해도 자동으로 Joint가 되지 않는다. `account:access`는 문서화된 일반 사용자 쓰기를 포함하는 위임이고, OIDC의 `openid profile arcade:read`는 별도의 로그인·읽기 권한이다. 두 종류를 같은 동의로 설명하지 않는다.

## 해결된 시작 경로 문제

### A 단방향 준비 상태와 흐름별 등록

[A 구현](../partner/client.py)·[홈](../partner/web.py)은 A 준비 조건과 Joint 준비 조건을 분리한다. A만 사용할 때 Joint 키는 필요 없다. 홈에서 A/B/Joint 목적과 시작 동작을 구분하고 흐름별 JSON과 세 언어 안내를 제공한다. 준비 상태는 설정 존재 여부이며 등록·자격증명 유효성·서버 도달성을 보증하지 않는다.

### B 전용 등록의 불필요한 A callback 요구

기존 검토에서 지적한 플랫폼 제약을 수정했다. 유효한 B 선언이 있으면 A를 생략할 수 있고, `/onboarding.json?flow=b`도 `direction_a` 자체를 생략한다. 개발자 센터에서 A를 끄고 B를 등록할 수 있다. 등록된 B 전용 앱은 파트너 자격증명만으로 제공자를 활성화하며, 뮤즈캣 발급 A 시크릿을 요구하거나 발급하지 않는다. A와 B 중 하나 이상은 필요하고, Musecat 로그인에는 A, Joint에는 A+B가 필요하다.

B 연결 성공은 Musecat 설정에서 연결 계정과 전적 조회로 확인한다. 샘플의 B grant 수는 토큰 교환된 권한 수이며 원격 캐시·프로필 노출 성공을 보증하지 않는다. 공개 프로필에는 파트너 공개 설정과 Musecat의 서비스 공개 설정을 모두 적용한다. 소유자는 연결한 서비스 탭에서 전적과 공개 설정을 확인할 수 있으며, 방문자에게는 공개된 서비스만 표시한다.

### 별도의 OIDC 로그인 예제

[OIDC 구현](../partner/oidc.py)은 Musecat 로그인으로 자체 세션을 만드는 흐름을 제공한다. `/onboarding.json?flow=login`은 기존 A/B/Joint 앱과 다른 ID 및 정확한 공개 origin의 `/oidc/callback`을 선언하고 `direction_a.login_enabled: true`를 설정한다. 개발자가 실제 연락처를 입력하고 등록을 저장한 뒤 별도 시크릿을 설정해야 한다.

`MUSECAT_LOGIN_CLIENT_ID`는 초기화 시 기본적으로 `PARTNER_ID + "_login"`으로 생성한다(ID 길이 제한 적용). `MUSECAT_LOGIN_CLIENT_SECRET`에는 그 로그인 앱이 발급받은 시크릿을 넣는다. Alice의 등록된 A/B/Joint 앱을 로그인용으로 수정하면 기존 grant에 영향을 줄 수 있으므로 별도 앱을 유지한다.

실행 흐름은 홈의 뮤즈캣 로그인 → Musecat 인증·동의 → 콜백 검증 → 별도 로컬 세션이다. PKCE S256, 세션에 묶인 state·nonce, RS256·`kid`·JWKS·issuer·audience·발급 시각·만료 검증과 UserInfo `sub` 일치를 확인한다. 로컬 ID는 issuer와 `sub`의 해시이며 데모 계정으로 자동 병합하지 않는다. 토큰은 서버에 암호화해 보관한다.

로그인은 최대 10분으로 토큰 만료를 넘지 않으며 자동 refresh가 없다. `/oidc/nearby`는 서울 중심 반경 5 km의 고정 읽기 예제이고 전체 오락실 목록을 제공하지 않는다. 로그아웃은 로컬 접근을 즉시 차단하고 worker의 영속 outbox로 토큰 회수를 재시도한다. Musecat 전체 세션이나 Alice의 별도 grant를 해제하지 않는다.

세 README에 앱 등록·환경변수·정확한 callback·로그인·조회·만료·로그아웃 절차가 있다. 실제 Preview OIDC 콜백, 읽기 API 조회, 로그아웃 후 권한 회수까지 검증을 완료했다. 자세한 범위는 [실측 기록](developer-api-test-results.md)을 참고한다.

### 오류별 복구 화면

[복구 처리](../partner/recovery.py)는 브라우저 요청에 원인·다음 행동·오류 코드·HTTP 상태를 세 언어로 표시한다. 프로토콜/API 엔드포인트는 JSON을 유지하고, 브라우저 경로도 `?format=json`으로 진단할 수 있다. 알려진 원격 오류 코드와 안전한 재시도 시간만 전달하며 토큰·원격 응답 원문을 표시하지 않는다.

| 오류 | 복구 행동 |
| --- | --- |
| `invalid_origin` | 정확한 HTTPS `PARTNER_ORIGIN`으로 접속; 터널 변경 시 설정·등록 URL 갱신 및 등록 갱신 |
| 설정 누락·`invalid_client`·잘못된 scope | 선택한 흐름과 앱 ID·해당 방향의 시크릿·승인 범위 확인 |
| callback 불일치 | 공개 origin과 정확한 등록 경로 확인; 콜백 우회 금지 |
| 잘못된 state·nonce·ID token | 같은 브라우저에서 새 로그인 시작; 콜백·코드 재사용 금지 |
| `invalid_grant`·만료 | 새 흐름 또는 재동의; 소비된 code/refresh 재사용 금지 |
| 동의 거부 | 이용자가 원하면 새 흐름 시작; 자동 반복 금지 |
| `records_private` | 파트너 공개 설정과 Musecat 프로필 공개 설정 확인 |
| HTTP 429 | 안내된 재시도 대기 시간 준수 |
| 원격 장애·잘못된 응답 | issuer·도달성·서비스 상태 확인 후 새 흐름 시작 |

## 개발자가 여전히 준비해야 하는 것

등록 JSON은 제출·승인이 완료된 상태가 아니다. 예시 연락처와 설명을 실제 서비스 정보로 바꾸고 HTTPS 도메인과 필요한 endpoint를 운영해야 한다. B만 선언할 때 A callback은 필요 없지만 B OAuth endpoint·서비스·scope는 필요하다. Joint는 추가 공동 연결 계약과 키 교환이 필요하다. 구조 검증과 conformance 통과도 실제 사용자 동의·전적 제공의 성공을 대신하지 않는다.

Quick Tunnel 주소가 바뀌면 issuer와 callback도 바뀐다. 안정적인 테스트에는 고정 도메인이나 named tunnel을 사용하고, `.env`의 암호화·세션 키를 유지한다. 비밀은 서버에만 보관하며 문서·스크린샷·이슈에 게시하지 않는다.

API 콘솔의 생성 예제에는 자리표시자가 있다. 모든 operation의 목록이 있다는 사실과 유효한 도메인 데이터·소유권·역할·위치·페이지네이션 등의 선행 조건을 만족한 실제 호출은 구분해야 한다. 일반 읽기 하나를 성공시킨 다음 필요한 API를 선택한다. 쓰기는 별도 확인을 거치며 모든 예제를 자동 실행하지 않는다.

## 검증 기록의 구분

이 문서는 현재 구현과 온보딩 절차를 검토한 보고서다. [Preview 실측 기록](preview-test-results.md)·[Developer API 검증 기록](developer-api-test-results.md)의 기존 결과를 새 B 전용 등록·OIDC 로그인·복구 화면의 배포 후 검증 결과로 간주하지 않는다. 남은 실행 확인은 별도 로그인 앱 등록·승인, 실제 callback 성공, 가까운 오락실 조회, 로그아웃 회수와 기존 Alice 연결 유지 여부다.
