# Pixelmon 서버 배치와 WebGUI 기본 화면 점검

2026-11-25 작업. 게임·Prism·서버를 실행하거나 종료하지 않고 파일과 저장된 로그를 검사했다. 실제 재접속과 메가진화는 사용자 확인 대기다.

## 서버 모드

바탕 화면의 `PIXELMON/mods`에 다음 세 파일을 추가했다.

| 파일 | 버전 | 역할 |
| --- | --- | --- |
| Pixelmon universal | 9.4.3 | 포켓몬과 전투 기반 |
| PocketMate_Mega.jar (EeveeMega 기반) | 1.1.0 | 범용 메가스톤 및 특성 등록 |
| pocketmate-mega-evolution | 0.1.1 | 포켓메이트 메가진화 폼·능력치·아이템 연결, 자산, API 호환 보완 |

기존 WebGUI 2.0.0과 Pocketmate Estates 0.15.4는 유지했다. 서버의 Estates JAR는 현재 로컬 배포본과 동일하다. 클라이언트 전용 모드 및 독립 Rinku는 추가하지 않았다. 메가진화 JAR에 데이터가 내장되어 서버 월드 폴더에 별도 데이터팩을 중복 설치하지 않았다. 서버와 접속 클라이언트 모두 세 모드가 필요하다.

후속 사용자 요청으로 EeveeMega 원본의 파일명과 모드 목록 표시명만 `PocketMate_Mega`로 변경했다. 내부 ID `eeveemega`, 버전 1.1.0 및 모든 코드·자산은 유지한다. 서버 배치 도구는 변경본 해시를 사용하며 원본과 변경본을 함께 설치하면 안 된다. 별도 포켓메이트 메가진화 보완 JAR는 계속 함께 필요하다.

## Prism 인스턴스의 서버 대상 모드 추가

같은 날 사용자 요청으로 `Pocketmate-PIXELMON-NeoForge` 인스턴스의 최상위 JAR 16개를 조사하고 서버에 아래 5개를 추가했다. 이들 전부가 접속 자체의 필수 조건이라는 의미는 아니다. 게임 기능과 해당 모드의 서버 기능을 적용하는 구성이다.

| 추가 파일 | 서버에 넣는 이유 |
| --- | --- |
| accessories-neoforge-1.1.0-beta.54+1.21.1.jar | 장신구 슬롯과 서버 동기화. [배포자 설명](https://modrinth.com/mod/accessories)의 양쪽 설치 대상 |
| owo-lib-neoforge-0.12.15.6-beta.1+1.21.jar | 설치된 Accessories 메타데이터가 요구하는 라이브러리 |
| Clumps-neoforge-1.21.1-19.0.0.1.jar | [경험치 구슬 병합 최적화](https://modrinth.com/mod/clumps)를 서버에 적용 |
| Jade-1.21.1-NeoForge-15.10.6.jar | 기본 HUD는 클라이언트만으로 가능하지만 [저장고 등 추가 정보는 서버 모드 필요](https://modrinth.com/mod/jade) |
| appleskin-neoforge-mc1.21-3.0.9.jar | [정확한 포만감·탈진 수치 동기화](https://modrinth.com/mod/appleskin?version=1.21.4)에 서버 모드 필요 |

제외: Korean Patch와 Mouse Tweaks는 입력·조작용, JEI와 mezz_config는 이번 구성에서 레시피 보기용, Xaero 미니맵·월드맵은 기본 지도 표시가 클라이언트에서 작동하므로 서버에 복사하지 않았다. JEI와 Xaero에 별도 선택적인 서버 기능이 있다는 것과 기본 사용에 서버 설치가 필요하다는 것은 구분한다. [Mouse Tweaks 배포자 설명](https://modrinth.com/mod/mouse-tweaks), [JEI](https://modrinth.com/mod/jei), [미니맵](https://modrinth.com/mod/xaeros-minimap), [월드맵](https://modrinth.com/mod/xaeros-world-map)도 확인했다.

Pixelmon, 두 메가 모드, WebGUI는 이미 서버와 같은 파일이었다. Estates는 같은 버전 번호이지만 클래스 5개가 달랐고 서버 쪽이 현재 소스 배포본과 동일하여 클라이언트의 이전 파일로 덮어쓰지 않았다. 설정·월드·클라이언트 파일 수정 없이 서버 JAR 5개만 새로 추가했다. 현재 서버 최상위 모드 JAR는 10개다.

설치 파일 해시와 CRC, owo 내장 라이브러리 6개 CRC, 중복 모드 ID와 선언된 서버 필수 의존성 존재를 검사했다. 실행 검증은 하지 않았으며 서버 재시작이 필요하다. 공개 정적 보고서는 `docs/evidence/reports/eeveemega/instance-server-mods-static.json`에 보관한다.

## 런처의 등록되지 않은 파일 오류

후속 스크린샷의 Accessories 차단은 서버 설치 문제가 아니라 로컬 런처의 `client-pack.json` 누락이었다. 실제 실행 중인 ClientPack 런처 폴더에는 모드 3개만 등록되어 있었다. `UpdateService.VerifyApprovedContent`는 `mods/*.jar`와 리소스팩의 등록 경로·용량·SHA-256을 검사하므로 나머지 파일도 차례로 차단될 수 있었다.

현재 인스턴스의 모드 18개와 사용 중인 복구 리소스팩 1개를 고정 해시로 등록했다. 기존 승인 항목 3개는 유지하고 16개 항목과 검증된 로컬 배포 사본을 추가했다. 새로 설치된 Sophisticated Backpacks/Core가 이번 목록에 포함되며, 서버에는 Backpacks가 이미 있어 빠진 Core 1.5.43.2504만 추가했다. 두 모드 메타데이터의 Minecraft/NeoForge/Core 요구 버전 및 설치 CRC를 확인했다. 현재 서버 최상위 JAR는 12개다. 앞선 10개 설치 검증은 당시 상태로 보존한다.

`tools/register_local_client_pack.py`는 운영자가 명시적으로 실행할 때 현재 로컬 콘텐츠를 등록하는 도구다. 게임 실행 때 자동으로 임의 파일을 승인하지 않는다. 런처 EXE·검증 로직·인스턴스 모드·리소스팩·옵션은 수정하지 않았다. 실제 `Services.cs`를 별도 검사 프로그램에 컴파일하여 `CheckLocal`과 `VerifyApprovedContent`를 현재 목록/인스턴스에 실행했고, 승인 파일19개·로컬 배포사본18개 검증 및 다운로드/제거 예정0개를 확인했다. 게임과 Prism은 실행하지 않았다.

기존 오류 창을 닫고 게임 시작을 다시 누르면 런처가 목록을 다시 읽는다. 배낭 라이브러리가 추가된 전용 서버는 재시작이 필요하다. 실제 게임 로딩과 서버 접속은 사용자 확인 대기다.

설치 전후 SHA-256 일치, 서버 최상위 JAR의 중복 모드 ID 부재, 기존 NeoForge 21.1.248 경로를 확인했다. 이는 Arclight에서의 실제 시작·배틀 호환성 검증을 의미하지 않는다.

## WebGUI에서 확인한 차이

- 전용 서버에는 이미 포켓메이트 HTML 및 관련 파일 260개가 있었고, 저장된 서버 로그도 해당 폴더의 260개 파일 제공을 기록했다. 17:34 클라이언트 저장 로그에도 같은 260개 manifest 수신이 있다. 전용 서버에서 HTML을 전혀 읽지 못했다는 원인은 확인되지 않았다.
- `Pocketmate-PIXELMON-NeoForge` 인스턴스의 로컬 WebGUI 폴더는 기본 예제 `index.html` 669바이트와 `hud.html` 두 개뿐이었다. 19:12와 19:41의 통합 서버 로그에서 예제 두 개 제공을 확인했다. 이 환경에서는 기본 화면이 나오는 직접적인 파일 차이가 있었다. 사용자 보고가 이 실행과 같은 상황인지는 미확인이다.
- 설치된 WebGUI 바이트코드에서 서버 `config/webgui/server.json`의 `bundledPagesDir`를 기준으로 웹 파일을 검색하고, 폴더가 없을 때 예제 페이지를 만드는 경로를 확인했다. F6 기본 메뉴는 서버가 보낸 메뉴 주소를 사용하며 빈 주소의 fallback은 WebGUI 공식 사이트다.

## 적용한 수정

- 명시적 웹 배포 목록 260개를 서버와 해당 테스트 인스턴스 양쪽에 맞췄다. 서버 웹 파일은 이미 최신 소스와 전부 같아 덮어쓸 변경이 없었으며, 테스트 인스턴스의 기본 index를 교체하고 관련 자산을 설치했다. 기존 추가 파일은 지우지 않았다.
- 두 환경의 `mainMenuUrl=webgui://index.html`, `serveBundledPages=true`, `bundledPagesDir=web`, `autoHudOnJoin=false`를 확인·적용했다. 서버 값은 이미 일치했고 클라이언트의 누락된 두 boolean 설정을 명시했다. 토큰 비밀키와 기타 설정은 보존했다.
- 서버 `run.bat`에 `cd /d "%~dp0" || exit /b 1`을 추가했다. 다른 작업 폴더에서 배치 파일을 호출할 때 경로가 달라지는 것을 예방한다. 이것이 이전 증상의 원인이었다고 단정하지 않는다.
- 원본/변경 파일 백업 및 전체 배치 보고서는 저장소 밖 `%LOCALAPPDATA%/PocketmateServerBackups/2026-11-25-mega-webgui`에 보관했다. 웹 시크릿 설정이 백업에 포함될 수 있으므로 공개 자료에는 원본 설정을 넣지 않는다.

재현 가능한 배치 도구는 `tools/deploy_pixelmon_server.py`다. 입력 모드 SHA-256을 고정하고 다른 이름의 중복 모드 ID가 있으면 쓰기 전에 중단한다. 웹 파일 목록은 기존 `package_estates.py`의 명시적 목록을 실행 없이 읽는다. 인수의 서버·클라이언트 경로는 실제 환경에 맞게 지정하고 매번 새 백업 경로를 사용한다.

## 적용과 남은 확인

새 모드가 있으므로 **서버와 게임을 완전히 종료한 뒤 다시 시작**해야 한다. `/webgui reload`만으로 새 모드와 Mixin이 적용되지는 않는다. 실행 중인 서버나 게임은 이번 작업에서 종료하지 않았다.

사용자가 재시작한 후 전용 서버에 접속하여 설정된 메뉴 단축키(Shift+F 또는 현재 키 설정)로 포켓메이트 메뉴가 나오는지 확인한다. 화면이 계속 기본 상태라면 해당 접속 직후 로그의 `server ships 260 page file(s)` 유무와 메뉴 URL 경고를 기준으로 추가 조사한다. 실제 UI·접속·메가진화·전투 검증 및 README 완료 표시는 보류했다.
