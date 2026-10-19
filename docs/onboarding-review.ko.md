# 신규 개발자 관점의 연동 온보딩 검토

검토일: 2026-10-20 (Australia/Sydney)

대상은 이 공개 샘플의 영어·한국어·일본어 README, 환경변수 예시와 초기화 스크립트, 홈 화면, A/B/Joint 구현, API 예제와 Musecat Backend Core의 등록·권한 계약이다. 소스와 체크인된 문서만 읽었다. 실제 `.env`, 계정 데이터, 실행 중인 연결, 네트워크와 배포 상태는 확인하지 않았다. 아래의 ‘이번 개선’은 현재 변경된 소스 및 함께 정비하는 문서의 범위이며, 새로운 실서비스 검증 결과를 뜻하지 않는다.

## 판단

프로토콜 예제와 API 목록은 이미 충분하다. 처음 온 개발자에게 가장 큰 장벽은 **어떤 연결을 선택하고, 어떤 정보와 키만 준비하며, 어디에서 성공을 확인해야 하는지**다. 기존 안내는 전체 A+B+Joint 예제를 실행하는 데 집중되어 단방향 연동도 양방향 설정이 필요한 것처럼 보였다.

| 목적 | 선택할 흐름 | 이 샘플에서 확인하는 것 |
| --- | --- | --- |
| 내 서버에서 사용자의 Musecat 기능을 호출 | A | Musecat OAuth 동의, `account:access`, 프로필/API 호출, refresh, 해제 |
| Musecat에 내 서비스의 사용자 전적을 제공 | B | 파트너 OAuth 동의, `profile` 및 `chunithm:read`, 가상 전적, 공개 범위, refresh |
| 두 방향을 공동 동의로 연결 | Joint | A와 B를 조정하는 공동 연결 및 양쪽 해제 |
| Musecat 계정으로 내 서비스에 로그인 | 별도 OIDC 예제 | 이 Flask 샘플에서는 구현하지 않음 |

A와 B는 각각 별도 grant와 토큰을 갖는다. 두 단방향 연결을 독립적으로 만들었다고 Joint가 되는 것은 아니다. Joint의 완료와 해제 의미는 공동 연결 계약을 따른다.

## P1 — 이번 샘플 개선으로 해결하는 시작 경로 문제

### 1. A 버튼이 Joint 키에 의존하던 문제

기존 홈은 `MUSECAT_CLIENT_SECRET`과 `PARTNER_TO_MUSECAT_KEY`를 하나의 준비 조건으로 묶어 A 버튼까지 비활성화했다. 하지만 [A 시작 처리](../partner/client.py)는 Client Secret만 요구한다.

이번 개선에서는 [홈 준비 상태](../partner/web.py)의 `a_ready`와 `joint_ready`를 분리하고 [화면](../partner/templates/index.html)에 A/B/Joint 각각의 목적과 시작 동작을 둔다. A만 사용할 때 Musecat 발급 Joint 키를 추가로 받아야 하는 장애를 제거한다.

이 준비 상태는 **로컬 설정 존재 여부**다. 승인 여부, 원격 자격증명의 유효성 또는 서버 도달 가능성을 보증하는 상태로 해석하면 안 된다.

### 2. B만 연결한 사용자가 성공을 확인하기 어렵던 문제

기존 홈은 A의 `link`만 읽고 연결 상태를 표시했다. B grant는 [파트너 OAuth 구현](../partner/oauth.py)의 `create_grant`/`issue_tokens`에 저장되지만 화면에서는 확인할 수 없었다. README의 실제 테스트 순서도 A 다음에 Joint를 안내해 독립 B의 시작을 찾기 어려웠다.

이번 개선에서는 B 카드에 Musecat 설정으로 이동하는 동작, 파트너 ID, 교환된 미회수 grant 수를 표시하고 README에 독립 B 테스트 경로를 추가한다. **Musecat 설정에서 일반 외부 연결을 시작하고 샘플에서 동의한 뒤 Musecat에서 전적을 조회한다**는 순서를 명확히 한다.

B grant 수는 샘플 내부에서 토큰 교환까지 진행된 권한의 수다. Musecat의 현재 연결 목록, 최근 전적 조회 성공, 프로필 노출 여부를 직접 조회한 결과가 아니다. 공개 전적 표시에는 파트너 공개 설정과 Musecat의 프로필 공개 설정을 함께 확인해야 한다. 독립 B 연결의 삭제와 Joint 양쪽 해제도 구분해야 한다.

### 3. 모든 개발자에게 전체 등록과 키 교환을 요구하던 안내

기존 [등록 JSON](../partner/web.py)은 항상 A+B+Joint를 포함했고 세 언어 README도 전체 설정을 입력하도록 안내했다. 초기화 스크립트가 여러 키를 생성한다는 사실과 실제 선택한 흐름에 필요한 키는 구분되어 있지 않았다.

이번 개선에서는 `/onboarding.json?flow=a|b|joint`와 흐름별 README 최소 설정 가이드를 제공한다. A 양식에서는 B와 Joint를 제외하고 B 양식에서는 Joint를 제외한다. 인자를 생략한 기존 `/onboarding.json`은 전체 Joint 예제에 해당한다.

| 자격증명 | 발급 주체와 전달 방향 | 필요한 사용 흐름 |
| --- | --- | --- |
| `PARTNER_ID` / Musecat Client ID | 등록 앱 ID와 샘플 설정을 일치시킴 | 앱 등록 공통; A client 및 B callback 식별에 사용 |
| `MUSECAT_CLIENT_SECRET` | Musecat → 샘플 서버 | A, Joint |
| `PARTNER_OAUTH_CLIENT_ID` / `PARTNER_OAUTH_CLIENT_SECRET` | 샘플 설정 → Musecat Direction B credential | B, Joint |
| `MUSECAT_TO_PARTNER_KEY` | 샘플 → Musecat의 파트너 발급 Joint 키 설정 | Joint |
| `PARTNER_TO_MUSECAT_KEY` | Musecat → 샘플 서버 | Joint |

샘플 초기화 시 B/Joint 관련 값을 생성·검증하는 것은 이 통합 데모의 실행 방식이다. A 프로토콜 자체가 파트너 OAuth 서버나 Joint 키를 요구한다는 의미가 아니다. [`.env.example`](../.env.example), [초기화 스크립트](../scripts/init-env.py), [시작 설정 검증](../partner/__init__.py)을 함께 참고한다.

## P1 — 샘플만으로 해결할 수 없는 플랫폼 등록 계약

### 4. B만 사용해도 Direction A callback을 등록해야 함

검토한 Backend Core `partnerapp/form.go`의 `Form.Validate`는 `direction_a.redirect_uris`를 조건 없이 1~8개 요구한다. `direction_b` 존재 여부나 실제 A 사용 여부에 따른 예외가 없다. 그러므로 현재 B용 샘플 등록 JSON에도 A callback을 유지한다. **B 실행에 Musecat Client Secret이 필요하다는 뜻은 아니며, 현 등록 양식의 필수 항목이라는 뜻**이다.

플랫폼에서 진정한 B-only 앱을 지원하려면 A 활성 여부를 표현하고 검증·승인·자격증명 발급·클라이언트 활성화 경로가 이를 일관되게 처리하도록 바꿔야 한다. 샘플에서 필드를 지우는 것만으로 해결할 수 없다.

관련 근거: Musecat Backend Core `partnerapp/form.go`의 `DirectionA`, `Form`, `Form.Validate` (`direction_a.redirect_uris` 검사).

### 5. 등록 JSON은 제출 완료 상태가 아님

생성된 JSON에는 실제 origin과 예제 설명이 들어가지만 `contact_email`은 `developer@example.com`이다. 개발자는 연락처와 앱 정보를 자기 서비스에 맞게 확인하고, Developer Center에 제출하고, 승인을 받은 뒤 필요한 credentials를 교환해야 한다. JSON에 비밀이 들어 있지 않은 것은 의도된 계약이다.

검토한 `Form.Validate` 기준 필수 정보는 지원하는 `spec`, 유효한 `partner_id`, 영어 `display_name`, 연락처 이메일, HTTPS A callback이다. `description`의 영어 값 및 `website`/`privacy_url`/`terms_url`/`support_url`은 이 구조 검증에서 필수가 아니며, 값을 넣으면 각 필드 검증을 받는다. B를 선언하면 OAuth endpoint, identity scope, 서비스와 서비스 scope 등이 필요하고, Joint를 켜면 B와 공동 연결 항목도 필요하다. 구조 검증 통과는 endpoint 도달성이나 운영 승인 통과를 보증하지 않는다.

따라서 ‘전체 JSON을 복사하면 연결 가능’보다 **양식 생성 → 실제 앱 정보 확인 → 제출·승인 → 흐름별 키 교환 → 재기동 → 연결 테스트**를 완료 기준으로 안내해야 한다. 임시 터널 주소가 바뀌면 등록 URL을 갱신하고 재승인·재연결해야 한다는 현재 README 설명은 유지할 가치가 있다.

## P2 — 권한 및 로그인 범위의 남은 설명 과제

### 6. `account:access`는 단순 프로필 조회 권한보다 넓음

[A 구현](../partner/client.py)은 `scope=account:access`를 요청하고 반환 scope도 해당 값으로 검증한다. ‘Musecat 프로필 조회’ 버튼만 보고 읽기 전용 프로필 연결이라고 해석하면 실제 권한 범위를 오해하게 된다.

Backend Core `docs/developer-api.md`의 ‘One connection, general user features’에 따르면 이 scope는 명시적으로 허용된 `/developer/v1/account` 일반 사용자 작업에 대한 위임이다. 프로필 조회뿐 아니라 프로필 수정, 커뮤니티 작성, 신고·방문 등 쓰기 작업도 포함한다. 다만 전체 API에 대한 무제한 권한은 아니다. 관리·계정 보안 작업 등은 제외되고 기존 소유권·역할·위치·공개 범위 검사가 유지된다. 프로필 조회 역시 모든 비공개 데이터를 무조건 공개하지 않는다.

샘플에서 가능한 보완은 A 설명에 ‘일반 사용자 기능 위임이며 쓰기 권한도 포함’이라고 적고 실제 권한 문서로 연결하는 것이다. 더 세분화된 새 권한 체계를 제공할지는 플랫폼 제품·계약 과제다. 기존 legacy narrow scope가 있다는 사실을 현재 샘플이 그 권한으로 동작한다는 의미로 소개해서는 안 된다.

### 7. OIDC는 Musecat에서 지원하지만 이 샘플은 로그인 예제가 아님

세 README는 이 샘플이 `openid profile arcade:read` 로그인 예제와 다르다고 이미 밝히고 있다. 실제 코드에도 OIDC `nonce`, `id_token` 검증, Musecat 로그인으로 자체 세션을 생성하는 흐름은 없다. 샘플의 `alice`/`bob` 로그인과 Musecat API 위임 연결을 따로 수행한다.

Backend Core `docs/sign-in-with-musecat.md`에는 별도 opt-in OIDC가 문서화되어 있다. `direction_a.login_enabled: true`를 등록·승인하고 `openid profile arcade:read`, state/nonce, PKCE, 서명·issuer·audience·만료 검증 등을 사용한다. 별도 `examples/musecat-signin` 예제도 있다. 따라서 ‘Musecat이 OIDC를 지원하지 않음’이 아니라 **공개 Flask 샘플이 해당 흐름을 시연하지 않음**이 정확하다.

최소 보완은 README 첫 선택표에서 로그인 목적을 별도 문서/예제로 연결하는 것이다. OIDC discovery나 JWKS가 API 목록에 보이는 것만으로 완성된 로그인 예제가 있다고 설명하면 안 된다. 검토는 소스 계약에 한정하므로 특정 배포의 OIDC signing key 설정·사용 가능 여부를 보증하지 않는다.

## P2 — 샘플에서 후속 개선 가능한 오류 안내

### 8. 오류 코드는 있지만 실패 원인과 다음 행동이 부족함

[공통 오류 처리](../partner/__init__.py)의 `ProtocolError`는 `{error: code}`와 상태 코드를 반환한다. [원격 호출](../partner/common.py)의 `remote`는 HTTP 오류를 포함하는 `URLError`와 응답 해석 실패를 `musecat_request_failed`로 묶는다. A/Joint 브라우저 흐름에서 승인·자격증명·callback·원격 장애를 구별하기 어렵다.

반면 [API 콘솔](../partner/explorer.py)은 HTTP 상태와 오류 본문을 보여준다. 따라서 ‘모든 API 오류가 사라진다’는 평가는 정확하지 않다. 개선 범위는 주로 연결 흐름의 브라우저 오류 화면과 공통 원격 호출 진단이다.

최소 문서 개선으로 다음 복구표를 추가할 수 있다. 추후 화면을 개선할 때도 코드와 HTTP 상태를 유지하고 비밀 값 없이 사용자 행동을 안내해야 한다.

| 증상·오류 | 확인할 내용과 다음 행동 |
| --- | --- |
| A 또는 Joint 시작 비활성 | 해당 흐름의 키 설정, 승인·발급 단계, 변경 후 컨테이너 재생성 |
| `invalid_client` | 등록 ID, 필요한 방향의 secret, 발급·회전 후 설정 일치 여부 |
| callback 또는 `invalid_request` | 등록된 정확한 callback, issuer, 현재 터널 origin; 임의 주소로 callback을 우회하지 않음 |
| `invalid_grant` | 만료·이미 사용된 code/refresh 여부; 소비된 토큰을 반복 재시도하지 않고 필요한 경우 재동의 |
| `records_private` | 파트너 공개 설정; 프로필 노출에는 Musecat 쪽 공개 설정도 확인 |
| HTTP 429 | 해당 조회 간격을 기다림; 새 인증·토큰 교환을 자동 반복하지 않음 |
| `musecat_request_failed` | 현재 코드는 상세 원인을 구분하지 못함; 연결 대상과 도달성을 확인하고 비밀 없는 진단 보완 필요 |

## P2 — 공식 문서와 예제의 역할 정리

검토한 Backend Core `docs/developer-api.md` 첫머리는 배포 URL 별도 전달, 운영자 수동 등록 및 Joint 제안 단계 중심의 표현을 남기고 있다. 공개 샘플은 Developer Center·Preview 주소·실제 Joint 흐름을 안내한다. 서로의 문서 역할과 현재 지원 상태를 맞추는 작업은 플랫폼 문서 과제다. 이 검토에서는 원격 정본 문서나 배포 상태를 직접 확인하지 않았다.

API 콘솔은 OpenAPI에서 파라미터·응답과 curl을 생성하는 유용한 탐색 도구다. 다만 [예제 생성기](../partner/api_examples.py)는 `<REPLACE>`, `<value>` 등 자리표시자를 생성한다. 카탈로그에 모든 operation이 있다는 사실은 각 예제가 유효한 도메인 데이터와 선행 조건을 갖춘 완결된 작업 절차라는 뜻이 아니다. 대표 읽기 호출 하나를 먼저 성공시키고 사용자 ID와 OAuth `sub`, 페이지네이션, 필요한 도메인 선행 조건을 설명한 뒤 전체 목록으로 연결하면 학습 순서가 명확해진다. 기존 쓰기 확인과 서버 측 토큰 보관은 유지해야 한다.

## 완료 범위와 후속 순서

이번 샘플 변경은 A/B/Joint 선택, A 독립 준비 상태, B 로컬 grant 표시, 흐름별 등록 JSON, 세 언어의 최소 설정·테스트 안내를 다룬다. 승인·자격증명 발급 계약이나 권한 체계를 바꾸는 작업은 포함하지 않는다.

후속 순서는 다음과 같다.

1. 플랫폼에서 B-only 등록의 A callback 필수 여부를 제품 계약으로 결정하고 관련 경로를 일관되게 정비한다.
2. 공개 안내에서 일반 API 위임과 OIDC 로그인의 선택, `account:access`의 쓰기 포함 범위를 명확히 한다.
3. 연결 오류에 비밀 없는 원인 구분과 복구 행동을 제공하고, 공식 등록·Joint 문서 표현을 현재 계약에 맞춘다.

이 보고서는 코드·문서 검토다. 기존 [Preview 실측 기록](preview-test-results.md)과 [Developer API 검증 기록](developer-api-test-results.md)을 새로운 변경의 실서비스 재검증 결과로 간주하지 않는다.
