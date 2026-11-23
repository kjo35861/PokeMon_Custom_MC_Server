# 증거 자료와 해석 범위

이 폴더는 기존 작업 중 실제로 남아 있던 자료의 공개용 사본이다. 원본 보고서가 가진 성공·미검증 표시를 유지한다. PC 절대 경로와 인증 필드는 정리하며, [manifest.json](manifest.json)에 원본 및 공개본 SHA-256·자료 종류·크기를 기록한다. 해시는 등록 이후 파일 동일성 확인용이며 제3자 검증 인증이나 과거 작성 시각 증명은 아니다.

## 최신 단계: 메뉴 0.12.0 / 모드 0.7.0

| 자료 | 확인할 수 있는 내용 | 한계 |
| --- | --- | --- |
| [프로필 공유 종합 기록](reports/webgui_menu/public-profiles-update-report.json) | 유저별 아이콘·배너, 기본 스킨 얼굴, 코드 검사 | 작성 당시 설치 대기와 게임 화면 미검증 표시를 유지 |
| [설치 상태](reports/webgui_menu/public-profiles-install.json) | 모드 파일 교체 `installed` | 새 모드로 플레이했다는 증거가 아님 |
| [ProfileStore JUnit](reports/estate_mod/TEST-space.pocketmate.estates.ProfileStoreTest.xml) | 착용·지급·실패 복구, 공개 조회의 비변경·공개 필드 범위 | 단위 검사 |
| [ClaimStore JUnit](reports/estate_mod/TEST-space.pocketmate.estates.ClaimStoreTest.xml) | 소유권·연결성·묶음 구매·원자성 | 단위 검사 |
| [경제 JUnit](reports/estate_mod/TEST-space.pocketmate.estates.EstateEconomyTest.xml) | 가격·한도·자금 순서·이관 | 외부 경제 모드 연동 검사가 아님 |
| [커뮤니티 JUnit](reports/estate_mod/TEST-space.pocketmate.estates.EstateCommunityTest.xml) | 초대·수락·권한·등급·삭제 | 실제 다중 접속 화면과 다름 |
| [지도 픽셀 JUnit](reports/estate_mod/TEST-space.pocketmate.estates.MapPixelCodecTest.xml) | 지형 픽셀 변환 | 실제 Xaero 세션 전체 검사와 다름 |
| [오버월드 정책](reports/webgui_menu/overworld-policy-report.json) | 기존 서버 제한 확인과 80가지 UI 요청 조건 | 실제 네더/엔드 초기화를 실행한 기록이 아님 |

최신 Node 검사 소스는 `webgui_menu/verification/check_appearance.cjs`, `check_estate_dimension.cjs`, `check_people.cjs`다. 최근 단계에서는 사용자가 게임 테스트를 맡기로 해, 게임 조작이나 최신 렌더링 캡처를 추가로 수행하지 않았다.

## 이전 단계의 실제 게임 및 브라우저 검증

- [영지 초기 통합 검증](reports/webgui_menu/estate-integration-report.json): 초기 청크 생성·확장·중복 거부와 실제 지형 표시 등 당시 관찰한 범위.
- [개인 프로필 통합 검증](reports/webgui_menu/profile-integration-report.json): 당시 실제 얼굴, 아이콘·배너 미리보기/저장 및 리로드 유지. 0.9 당시의 제한도 그대로 적혀 있다.
- [영지 경제 브라우저 검사](reports/webgui_menu/estate-economy-browser-report.json): 모의 서버를 사용하는 화면 계약 검사.
- [런처 백엔드 검사](reports/snowfrost_launcher/backend-report.json): 경로·manifest·롤백·Prism 명령 구성 등 46개 항목.
- [Prism 실행 관찰](reports/snowfrost_launcher/prism-ui-play-report.json), [런처 최종 기록](reports/snowfrost_launcher/final-report.json): 당시 실제 실행/종료 확인과 배포 기본값.
- `reports/timing_helper/`: 이전 영상·모의 노트·타이머 분석. 실제 새 버전 게임 판정 성공률과 구별한다.

## 화면 자료

아래 파일은 **과거 화면**이다. 최신 화면처럼 재생성하거나 수정하지 않고 보관한다.

| 파일 | 설명 |
| --- | --- |
| [일반 메뉴](screenshots/historical-menu-redesign.png) | 초기 재설계 단계, 이전 로고·문구가 남아 있음 |
| [영지 광장](screenshots/historical-estate-plaza.png) | 영지 커뮤니티 이전 단계의 화면 |
| [영토 지도](screenshots/historical-estate-map-mock.png) | 브라우저 모의 소유권 화면. 사선 배경은 실제 지형 증거가 아님 |
| [금고·성장](screenshots/historical-estate-treasury.png) | 과거 성장·결제 화면 검사 자료 |
| [프로필 편집](screenshots/historical-profile-studio.png) | 이전 배너 편집과 미리보기. 최신 사용자 공유 표시가 아님 |
| [Prism 런처](screenshots/historical-launcher-prism-0.3.0.png) | 0.3.0 화면. 제거 전 실행 횟수가 보일 수 있음 |
| [사용자 제공 카드](screenshots/user-reported-before-0.12.0-profile.png) | 0.12.0 수정 요청에 첨부된 수정 전 화면 |
| [사용자 제공 광장 표](screenshots/user-reported-before-0.12.0-plaza-members.png) | 이니셜 표시 개선을 요청한 수정 전 화면 |
| [사용자 제공 관리 표](screenshots/user-reported-before-0.12.0-members.png) | 사용자별 아이콘·배너 연결 전 화면 |

`artwork/`에는 대표 이미지의 실제 생성·수정 프롬프트 기록을 보관한다. 원본 영상, 제3자 모드 JAR·전체 디컴파일 출력, 개인 월드·계정 파일은 포함하지 않는다.

## 자료 갱신

```powershell
python tools/prepare_evidence.py
python tools/prepare_evidence.py --check
python tools/check_publish.py
```

자료를 갱신할 때 최신 결과와 이전 기록을 구분한다. 이전 보고서에 없던 검사를 사후에 통과했다고 덧붙이지 않는다. 원본을 다시 제공하지 않은 체크아웃에서는 이미 보관된 증거를 삭제하지 않는다.
