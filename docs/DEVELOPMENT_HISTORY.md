# 개발 과정 상세 기록

정리일: 2026-11-24, Asia/Seoul. 이 문서는 요청과 구현 순서를 정리한 회고 기록이다. 개별 단계의 실제 날짜가 확인되지 않는 경우 날짜를 추정하지 않았다. 최초 Git 등록 이전 단계는 각각의 커밋으로 존재하지 않는다.

## 런처

1. 참고 화면을 바탕으로 배경·서버 제목·시작 버튼·상태/안내 카드를 갖춘 WPF 기본 런처를 구성했다.
2. 서비스명을 포켓메이트로 통일했다.
3. Minecraft 1.21.1 고정, 서버 manifest 확인, 업데이트 버튼 전환, 다운로드·무결성 검사와 실패 복구를 구현했다.
4. Microsoft 직접 로그인 경로를 검토했으나 최종 제품 흐름은 Prism 연결로 전환했다. 현재 실행은 `PrismBridge.cs`를 통하며 레거시 인증·설치 코드는 별도로 남아 있다.
5. 기본 순정 인스턴스와 서버 모드 인스턴스를 분리하고, 서버 미지정 시 순정 1.21.1을 실행하도록 했다.
6. 서버 팩 기본값을 Fabric으로 잡고 실행 횟수 표시는 제거했다. 최종 런처는 0.3.1이다.

근거: `docs/evidence/reports/snowfrost_launcher/`의 백엔드·Prism 실행·최종 보고서. 과거 0.3.0 스크린샷에는 제거 이전 실행 횟수 표시가 있으므로 최신 상태와 혼동하지 않는다.

## WebGUI와 영지의 단계별 개선

| 단계 | 요청/문제 | 구현·조정 | 검증 자료 |
| --- | --- | --- | --- |
| 기본 메뉴 | 싱글에서 메뉴 틀을 테스트 | WebGUI 페이지와 기본 탐색·안내 | `browser-report.json`, `final-report.json` |
| 디자인 재설계 | 기존 테마 교체, 외곽에 인게임 배경 표시 | 투명 외곽과 새로운 메뉴 레이아웃 | `redesign-browser-report.json` |
| 왼쪽 탭·글자 조절 | 읽기 쉬운 탭과 크기 버튼 | 왼쪽 탐색, 80~160% 크기 저장 | `left-tabs-text-report.json`, `scaled-tabs-report.json` |
| 초기 영지 | 현재 무주 청크 생성, 인접 청크 확장 | 서버 소유권 저장, 대각선·중복 구매 거부 | `estate-integration-report.json` |
| Xaero 지도 | 실제 지형 품질 | 읽기 전용 지형 브리지, 지도 이동·확대, 요청 큐 개선 | `estate-v0.5-integration.txt`, `estate-v0.6-integration.json` |
| 묶음 구매 | 청크 클릭으로 선택/취소 | 전체 선택의 연결성 검사·일괄 저장 | `estate-browser-report.json` |
| 전용 관리소 | 작은 메뉴에서 분리 | 전체화면 배경과 큰 관리 창 | `estate-v0.7-integration.json` |
| 영지 커뮤니티 | 이름, 광장 이미지·공지, 마을원 | 초대 수락, 등급 조정·추방, 마지막 접속 | `estate-community-browser-report.json`, `estate-v0.8-integration.json` |
| 삭제·테마·폰트 | 삭제 확인 강화와 일관성 | 이름 일치 확인, 배경색 통일, 무료 폰트 | `theme-background-report.json` |
| 지도 범위 | 256 표시는 과도함 | 기본 배율과 최대 축척 단위 128블록 조정 | `estate-v0.8.5-integration.json` |
| 프로필 / 0.9 | 칭호·아이콘·배너 | 소유 항목 검사, 미리보기/저장, 실제 스킨 얼굴 | `profile-integration-report.json` |
| 금고·성장 / 0.10 | 레벨·한도·단가와 자금 순서 | 0~10레벨, 최대 36청크, 금고 우선·영주 보충 | `estate-economy-browser-report.json`, `estate-v0.10-integration.json` |
| 0.10.1 | 정원과 성장 표 누락 | 전 레벨 정원 5명, 표·스크롤·최대 인원 | `member-limit-install.json` |
| 0.10.2~0.10.3 | 텍스트 이모지 교체, 칭호 아이콘 누락 | 24종 SVG와 보유 칭호 렌더링 통일 | `icons-update-report.json`, `title-prefix-update-report.json` |
| 0.10.4~0.10.7 | 대표 이미지 반복 개선 | 투명 PNG, 단순화, 별·보석 복원, 공통 배경용 색 | `brand-image-update-report.json`, 이미지 프롬프트 |
| 0.10.8~0.10.9 | 로고 확대와 정렬 | 배치 영역은 유지하고 이미지 시각 크기·위치만 조정 | `brand-size-update-report.json` |
| 0.11.0 | 라이트·다크 모드와 오탈자 | 두 메뉴 공통 테마·저장, 제목 밑줄→마침표 | `appearance-update-report.json` |
| 0.11.1~0.11.2 | 배너 위 글자·SVG 가독성 | 밝은 글자·칭호색, 비례 크기·선 굵기·정렬 | `profile-contrast-update-report.json` |
| 0.11.3 | 모드 설명 제거와 오버월드 한정 | 불필요 문구 제거, UI 요청 차단·차원 이동 정리 | `overworld-policy-report.json` |
| 0.12.0 / 모드 0.7.0 | 1px 경계와 다른 유저의 꾸미기 | 단일 배경 합성, 표 셀 복구, 유저별 착용 공유·스킨 조회 | `public-profiles-update-report.json`, 최신 JUnit 결과 |

위 보고서 파일은 `docs/evidence/reports/webgui_menu/`에 공개용 사본을 보관한다. 서로 다른 단계의 보고서를 최신 전체 제품 검증으로 합쳐 해석하지 않는다.

## 최초 등록 시점의 상태와 남은 확인

- 0.7.0 Java 빌드·JUnit 50개 통과 기록이 있다.
- 메뉴 로직 검사에서 차원/요청 조합 80개, 테마 저장과 유저별 이미지 연결을 확인했다.
- 모드 교체 보고서는 `installed`이며, 이전 종합 보고서 안의 `waiting_for_game_to_release_old_jar`는 작성 당시의 상태로 보존했다.
- 최신 실제 게임 화면과 다중 접속 시 다른 유저의 스킨·배너 표시는 사용자가 추가 확인해야 한다. 최근 작업에서는 게임을 자동 조작하지 않았다.
- 경매장·거래소, 실제 경제 모드, 블록 보호, 운영 서버와 차원 초기화 등 미구현 범위는 README에 적었다.
- 삭제 요청된 건축 맵을 복원하거나 계정·월드·실행 파일을 함께 올리지 않았다.

## 이후 기록 규칙

매시간 실행은 실제 변경이 있을 때만 아래 정보를 남긴다.

1. 무엇을 바꿨는지, 요청 또는 문제와 결과.
2. 변경된 구성 요소와 적용 방법(리로드/재시작).
3. 실제 수행한 검사와 그 한계. 실행하지 않은 검사는 통과했다고 쓰지 않는다.
4. 관련 보고서·스크린샷·소스 링크와 커밋.

향후 날짜별 기록은 `docs/worklog/YYYY-MM-DD.md`에 추가한다. 최초 등록 이전 기록은 이 회고 문서로 남긴다.
