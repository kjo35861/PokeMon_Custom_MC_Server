# 타사 자료와 출처

- Minecraft·Microsoft·Prism·Fabric·WebGUI·Xaero 프로그램은 저장소에 재배포하지 않습니다. 이름은 호환 환경과 연결 대상을 설명하기 위해 사용합니다.
- 포켓몬 이미지·캐릭터와 관련 표장은 원 권리자의 자료입니다. `webgui_menu/profile-assets/`의 기존 출처·라이선스 안내를 함께 확인하세요. 이 저장소가 해당 캐릭터의 권리를 소유한다는 의미는 아닙니다.
- NanumSquareRound 폰트는 [동봉된 라이선스](webgui_menu/NanumSquareRound-LICENSE.txt)를 유지합니다. `fonts.css`에는 폰트가 포함돼 있습니다.
- 런처 배경의 생성 기록은 [background-prompt.md](pocketmate_launcher/assets/background-prompt.md), 대표 아이콘의 생성·수정 기록은 [증거 자료](docs/evidence/artwork)에 있습니다.
- SVG 배너·메뉴 아이콘, 코드와 자료의 기존 개별 라이선스 표기는 유지합니다. 이번 정리 작업으로 타사 자료를 포함한 저장소 전체에 새로운 일괄 라이선스를 부여하지 않습니다.

## Gowun Dodum (게임 기본 글꼴)

Copyright 2021 The Gowun Dodum Project Authors. SIL Open Font License 1.1.
원본: https://github.com/google/fonts/tree/main/ofl/gowundodum
수정하지 않은 TTF 및 라이선스: `estate_mod/src/main/resources/assets/pocketmate/font/`. 라이선스 전문 `gowun_dodum_ofl.txt`를 모드에 함께 포함한다.

## Galmuri9 (현재 게임 기본 글꼴)

제작: quiple (Lee Minseo). 원본: https://github.com/quiple/galmuri
SIL Open Font License 1.1. 원본 TTF와 라이선스 전문은 `estate_mod/src/main/resources/assets/pocketmate/font/galmuri9.ttf`, `galmuri_ofl.txt`에 포함한다.

## EeveeMega 호환 데이터 생성

`estate_mod/mega_compat/catalog.json`의 포켓몬 타입·수치·특성 정보는 Pokémon 공식 발표 및 [Pokémon Showdown의 고정 데이터](https://github.com/smogon/pokemon-showdown/blob/7244fe8e28fa8bc4d0809ae30d183c608b62bb2b/data/pokedex.ts)를 참조한다. 공식 웹에 없는 전체 수치표를 공식 웹 자료로 표기하지 않는다. Pixelmon의 종족 원본 JSON과 사용자가 제공한 모델·텍스처는 로컬 빌드 입력으로만 읽으며 저장소에 포함하지 않는다. 자체 보완 모듈은 원본 Pixelmon/EeveeMega 클래스를 재배포하지 않는다. 구체적인 생성·검증 범위는 `docs/EEVEEMEGA_FORM_PACK.md`에 기록한다.
