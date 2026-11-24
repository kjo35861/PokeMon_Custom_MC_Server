# 일반 선 PNG 칭호 아이콘 · 검토용 3차

상태: **사용자 검토 대기 · 게임 미설치 · 실제 게임 표시 미검증**.

사용자가 픽셀아트 대신 일반 선 아이콘을 요청해 2차 문양의 선과 곡선을 유지한 투명 PNG 94개를 준비했다. 문구·색·종별 모티프는 유지했다. PNG는 48×48이며 둥근 선 끝과 가장자리의 부드러운 알파를 사용한다. 픽셀 격자에 맞춘 도트 도형이 아니다. 편집 기준은 상위 폴더의 도형 데이터이지만, 게임에서 읽을 파일은 PNG와 글꼴 JSON뿐이다.

## 준비한 파일

- `icons/<도감번호>.png`: 각 포켓몬의 투명 PNG 원본 94개.
- `resource-pack/`: 향후 설치할 수 있도록 분리해 둔 **미설치 초안**.
- `resource-pack/assets/pocketmate/font/legendary_titles.json`: `pocketmate:legendary_titles` 비트맵 글꼴.
- `resource-pack/assets/pocketmate/textures/font/legendary_titles.png`: 16열×6행, 48px 셀의 768×288 PNG 시트.
- `glyph-map.json`: 도감 번호·칭호·색·전용 문자 매핑. U+E100부터 94개를 할당한다.
- `tellraw-examples.txt`: 향후 수동 검사에 쓸 명령 예시 94개. 이번 작업에서는 실행하지 않았다.
- `legendary-lines.png`, `mythical-lines.png`: 전체 비교판. 실제 게임 스크린샷이 아니다.

글꼴 높이 9·기준선 8로 정의해 채팅 글자 옆에 들어가도록 준비했다. PNG 셀 크기 48과 실제 글꼴 높이 9는 별개다. 게임에서는 9 단위 높이로 축소해 그리므로 실제 렌더러·GUI 배율에서의 선 두께·가독성은 설치 후 확인해야 한다. 현재 모드에 이 글꼴이나 포획 보상 로직을 연결하지 않았다.

아이콘 PNG 자체에 색이 있으므로 아이콘 문자에는 **white** 색을 지정한다. 칭호 색은 뒤의 문구에 별도로 지정하고 일반 문구는 `minecraft:default` 글꼴로 돌려놓는다. 아이콘에도 칭호 색을 다시 적용하면 텍스처 색과 곱해져 색이 어두워질 수 있다. 받는 클라이언트에 이 리소스가 실제 제공·활성화되어야 보인다.

팩 메타데이터는 대상 Minecraft 1.21.1용 형식 34로 준비했다. 버전 계열의 리소스 팩 형식 34는 [공식 1.21 기술 변경 안내](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21)에 명시되어 있다. 실제 프로젝트 대상 1.21.1의 비트맵 글꼴 자산 구성도 참고했다.

## 검사와 적용 범위

`python tools/build_line_title_pngs.py`로 생성하며 게임·Prism·설치 디렉터리를 읽거나 쓰지 않는다. `python tools/check_line_title_pngs.py`로 PNG 투명도/부드러운 알파·폰트 셀·문자 매핑·팩 메타데이터·명령 예시 JSON을 검사한다. `node tools/check_title_designs.cjs docs/design/legendary-titles/line-png-v3`로 검토 화면의 188가지 선택/테마 상태를 검사한다. 이것은 정적·모의 DOM 검사이며 Minecraft 로딩이나 실제 브라우저 검증이 아니다.

전체 비교판 2장을 직접 열어 선 아이콘 렌더링을 확인했다. 마인크래프트에는 설치하지 않았으며 `/webgui reload`, 재시작이나 명령어 실행은 하지 않았다. 픽셀아트로 진행하던 중 사용자가 방향을 정정했으므로 해당 임시안은 공개 대상에서 제외했다.
