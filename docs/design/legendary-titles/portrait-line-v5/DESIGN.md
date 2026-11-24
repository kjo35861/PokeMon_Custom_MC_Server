# 외형 기반 포켓몬 선 아이콘 · 5차 시안

상태: **사용자 검토 대기 · 게임 미적용 · 실제 게임 표시 미검증**.

이번 기준은 사용자의 최신 요청인 '선을 사용하되 외형·컨셉·칭호를 함께 납득할 수 있는 아이콘'이다. 전설 71종과 환상 23종의 일반적인 기본형을 기준으로 각각 다른 얼굴·몸의 윤곽을 새로 그렸다. 앞선 추상 문양을 다시 쓰거나 전체 포켓몬에 공통 상징만 붙이는 방식은 사용하지 않았다. 외형을 보고 곧바로 알아볼 수 있는지는 최종 사용자 검토가 필요하다.

## 제작 기준과 자료

`tools/build_portrait_title_icons.py`에 94종별 윤곽·세부 특징·칭호와의 관계를 기록했다. 32×32 좌표에서 직접 단순화한 드로잉을 48×48 투명 PNG로 렌더링한다. 상위 폴더의 칭호 문구·색은 유지한다. 작은 크기에 맞춰 눈·턱·뿔·볏·날개처럼 식별에 필요한 부분을 우선 남기고, 컨셉은 그 포켓몬의 실제 구조와 연결되는 경우만 더했다.

예를 들어 크레세리아는 초승달 머리와 고리 날개, 라이코는 이마 철판·구름 갈기·긴 송곳니, 레지드래고는 거대한 용 턱과 둥근 핵, 자시안은 검을 문 늑대, 오거폰은 실제 벽록 가면의 눈·이빨을 남겼다. 종별 전체 근거는 `design-rationale.json`과 `종별 디자인 기준.md`에 있으며 검토 화면에서도 선택한 종의 설명을 볼 수 있다.

외형 확인에는 [PokeAPI sprites의 official-artwork 디렉터리](https://github.com/PokeAPI/sprites/tree/master/sprites/pokemon/other/official-artwork)의 94종 이미지를 로컬 참고 자료로 열어 확인했다. 이 디렉터리는 원화의 미러이며 Pokémon 공식 배포 사이트가 아니다. 참고 이미지를 공개 자료에 복사하거나 최종 아이콘에 그대로 붙이지 않았다. 원화 다운로드·참고 비교판은 무시되는 로컬 검증 백업에만 보관한다.

## 파일과 검사

- `icons/`: 종별 PNG 94개.
- `design-rationale.json`, `종별 디자인 기준.md`: 외형 특징과 칭호의 관계.
- `legendary-portraits.png`, `mythical-portraits.png`: 검토용 비교판. 실제 게임 화면이 아니다.
- `resource-pack/`, `glyph-map.json`, `tellraw-examples.txt`: 이전과 같은 대상 1.21.1용 비트맵 글꼴 초안과 예시. 미설치·미실행 상태다.
- `preview.fragment.html`, `preview-data.json`: 대화 내 검토 화면 원본.

생성은 `python tools/build_portrait_title_icons.py`, 정적 검사는 `python tools/check_line_title_pngs.py docs/design/legendary-titles/portrait-line-v5`, 검토 화면 모의 검사는 `node tools/check_title_designs.cjs docs/design/legendary-titles/portrait-line-v5`로 한다.

94종의 이름·문구·색 보존, 개별 도형과 외형/칭호 근거 존재, PNG 투명도·문자 시트·폰트 매핑·명령 JSON을 검사했다. 188개 선택/테마 상태에서 새 설명도 갱신되는지 검사했고 비교판 PNG 2장은 직접 열어 확인했다. 실제 브라우저·Minecraft·9px 채팅 크기에서의 인식성은 검사하지 않았다. 특히 얼굴의 미세한 특징은 게임 표시 높이·GUI 배율에서 추가 조정이 필요할 수 있다.

게임/Prism 실행·종료·조작과 설치 파일 변경은 하지 않았다. 이전 컬러 시안은 사용자의 방향 정정으로 미공개 로컬 백업에 보관했으며, 기존에 공개된 1~3차 시안과 기록은 유지한다. 이번 시안의 사용자 승인 전에는 README의 완료 기능으로 기록하지 않는다.
