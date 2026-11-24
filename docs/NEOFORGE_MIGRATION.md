# 픽셀몬 1.21.1 · NeoForge 전환 가능성 조사

2026-11-25 사용자 지정: 포켓몬은 Cobblemon이 아닌 **Pixelmon**. 현재 환경을 바로 전환하지 않고 전환 가능 여부를 조사했다.

## 결론

**NeoForge 1.21.1로 전환 가능하다.** WebGUI와 Xaero 월드맵의 네이티브 NeoForge 배포본이 있어 메뉴를 버릴 필요는 없다. 다만 자체 Fabric 모드 JAR를 그대로 옮겨도 된다는 의미는 아니다. 실제 게임 부팅·연동 호환성은 아직 검증하지 않았다.

|구성|조사 결과|필요한 작업|
|---|---|---|
|Pixelmon|1.21.1 NeoForge 배포|서버·클라이언트에 같은 호환 버전 설치|
|WebGUI|2.0.0+mc1.21.1-neoforge 배포 확인|Fabric JAR 대신 NeoForge JAR와 필수 Rinku 설치|
|메뉴 HTML/CSS/JS·아이콘|일반 웹 자산|디자인 재사용, 메시지 API 동작 확인|
|Xaero 월드맵|1.21.1 NeoForge 배포 확인|동일 기능의 NeoForge 빌드로 교체, 맵 브리지 재검증|
|영지·프로필·닉네임·임무 저장 규칙|자체 Java 자료 모델|저장 형식을 유지하며 공통 코드로 재사용 가능|
|서버 이벤트·명령어|Fabric API 사용|NeoForge 이벤트·명령어 등록으로 이식|
|클라이언트 네트워크·맵·스킨 브리지|Fabric API 사용|NeoForge payload/클라이언트 이벤트로 이식|
|Mixins|Yarn 클래스/메서드 사용|Mojang 이름과 대상 동작을 확인해 재매핑·재검증|
|WebGUI 반투명 보완 모드|현재 Fabric 전용|NeoForge WebGUI의 기본 반투명 지원부터 확인, 필요 시 보완 모드 이식|
|고유 칭호·폰트 자산|Minecraft 공통 리소스|폰트 경로와 자산 재사용, 표시 검증|
|Prism 연동 런처|현재 기본값 Fabric|새 NeoForge 인스턴스를 지정하는 설치·실행 설정 준비|

현재 인스턴스/월드/런처 기본값은 조사만으로 바꾸지 않았다. 새 NeoForge 테스트 인스턴스로 병행 검증하는 것이 적절하다. Sinytra Connector는 일부 Fabric 모드를 실행하는 대안이지만, 모든 자체 Mixin·네트워크·브라우저 보완의 호환성이 입증된 것이 아니므로 네이티브 이식을 우선한다.

## 확인한 공식 자료

- Pixelmon 공식: https://reforged.gg/en / https://pixelmonmod.com/downloads.php
- WebGUI 공식 설치 가이드(NeoForge/Rinku): https://webgui.space/guide/getting-started.html
- WebGUI 소스: https://github.com/mc-webgui/webgui
- WebGUI 공식 Modrinth 배포 API: https://api.modrinth.com/v2/project/webgui/version?loaders=%5B%22neoforge%22%5D&game_versions=%5B%221.21.1%22%5D
- Xaero 공식 Modrinth 배포 API: https://api.modrinth.com/v2/project/xaeros-world-map/version?loaders=%5B%22neoforge%22%5D&game_versions=%5B%221.21.1%22%5D
- Pixelmon 처치 이벤트: https://reforged.gg/docs/1211/com/pixelmonmod/pixelmon/api/events/BeatWildPixelmonEvent.html
- Pixelmon 포획 이벤트: https://reforged.gg/docs/1211/com/pixelmonmod/pixelmon/api/events/CaptureEvent.html
- Pixelmon 경험치 이벤트: https://reforged.gg/docs/1211/com/pixelmonmod/pixelmon/api/events/ExperienceGainEvent.html
- Connector 공식: https://github.com/Sinytra/Connector

Modrinth 배포 목록에서 WebGUI `2.0.0+mc1.21.1-neoforge`(2026-10-13), Xaero `neoforge-1.21.1-1.47.0`(2026-10-05)을 확인했다. 이는 배포본 존재 확인이며 포켓메이트 조합으로 게임을 실행해 통과한 증거는 아니다.

## 이식 후 필요한 검증

별도 테스트 인스턴스에서 메뉴 열기·반투명·서버 메시지, 영지 생성/연결 구매/금고/마을원/이동, 닉네임과 칭호 채팅, 폰트, 지도·프로필·클라이언트 통신을 점검한다. 픽셀몬은 실제 포획/처치/승리 이벤트에 일일 임무를 연결하고 PvP·포획 종료·취소·중복 이벤트를 제외한다. 지급 보상이 정해지기 전에는 수령 기록만 저장한다.

이 문서는 조사 결과이며 NeoForge 이식·픽셀몬 설치·실제 연동 완료를 뜻하지 않는다.
