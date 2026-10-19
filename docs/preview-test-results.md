# Preview 실측 검증

검증일: 2026-10-19 (Australia/Sydney).

로컬 Docker Compose의 app/worker를 임시 HTTPS 터널로 노출하고, 실제 `preview.musecat.app` 및 `db-dev.musecat.app`에 별도 테스트 앱을 등록해 검증했습니다. Mock Musecat 서버를 사용한 결과가 아닙니다.

## 실제 연동 검사: 14개 통과

1. local Compose and public HTTPS tunnel with real Preview app registration and bilateral keys
2. ordinary Direction A OAuth, profile read and actual refresh rotation against Preview
3. ordinary disconnect delivered by persistent local worker
4. partner-initiated joint flow, one consent, both code exchanges and confirmed bilateral status
5. partner private records are withheld by the actual Musecat adapter
6. Direction B real 401 refresh retry, envelope validation and subject stripping
7. both privacy gates, anonymous profile records and deployed profile rendering
8. partner-side bilateral disconnect delivered to Preview and both legs revoked
9. Musecat-initiated joint flow returns to Preview only after both sides confirm connected
10. Musecat-side bilateral disconnect arrives at the local Docker sample
11. fresh bilateral reconnection after revocation
12. ordinary Direction B consent, session-bound Preview callback and actual record fetch
13. joint denial issues no reciprocal grant and preserves pre-existing independent connection
14. live invalid CSRF, wrong bearer and unregistered OAuth callback rejection

## 로컬 검증

- 프로토콜 단위 테스트 9개 통과: PKCE·재사용·scope·private·세션 바인딩·멱등·세대 격리·만료·키 교체·outbox·불확실한 refresh 처리.
- Docker Compose 구성 검증과 실제 이미지 빌드·app healthcheck·별도 worker 실행 확인.
- 테스트용 관리자 자격증명과 OAuth 토큰은 이 저장소에 포함하지 않습니다.

## 재현

README의 등록·키 교환 절차와 실제 테스트 순서를 따릅니다. Preview 앱 승인이 필요하며 이 저장소를 실행하는 것만으로 권한이 발급되지 않습니다. 임시 터널 URL이나 검증에 사용한 계정 ID는 재사용하지 않습니다.
