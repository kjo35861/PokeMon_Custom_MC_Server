# 마인크래프트 고운돋움 글꼴

Minecraft Java 1.21.1 / 포켓메이트 모드 0.10.4부터 클라이언트 기본 글꼴 `minecraft:default`에 Gowun Dodum Regular를 등록한다. 웹 임베드나 온라인 글꼴 요청 없이 JAR에 포함된 TTF를 사용한다.

- 원본: https://github.com/google/fonts/tree/main/ofl/gowundodum
- 재배포: SIL OFL 1.1. 원본 TTF와 저작권·라이선스 전문 포함.
- 기본값: size 9, oversample 3, shift [0, 0]. 실제 게임 크기·자간·행간은 사용자 확인 대기.
- 공백은 바닐라 space 공급자를 사용하고 지원하지 않는 글자는 바닐라 default/unifont로 보완한다. 더 높은 우선순위의 글꼴 리소스팩이나 자체 글꼴을 쓰는 다른 모드 화면은 해당 설정을 따를 수 있다.
- 기존 `pocketmate:titles`, `pocketmate:legendary_titles`는 별도 비트맵 폰트로 유지하므로 칭호 아이콘을 일반 글꼴로 대체하지 않는다.
- 클라이언트 모드 교체이므로 게임 재시작 필요. `/webgui reload`는 적용 방법이 아니다. WebGUI의 CSS 글꼴과 게임 글꼴은 별개다.

정적 검사: 한글 완성형 11,172자 및 영문·숫자 cmap, 폰트 fallback, 칭호 비트맵 분리, 빌드 JAR 내 파일 동일성 확인. Java 68개 테스트 및 빌드 통과. 게임 실행·화면 조작·실제 게임 표시 확인은 하지 않았다.

## 0.10.3 로딩 실패 수정

사용자 게임 로그에서 `pocketmate:font/font/gowun_dodum.ttf` 누락과 `Default font failed to load` 확인. TTF 공급자가 `font/`를 자동 추가하므로 file을 `pocketmate:gowun_dodum.ttf`로 수정. 대문자 라이선스 리소스 경고도 소문자 파일명으로 수정. 이전 정적 검사에는 실제 로더의 경로 변환 검사가 빠져 있었으며 이를 추가했다. 재실행 확인 전까지 해결 검증 대기.
