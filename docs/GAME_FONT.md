# 현재 게임 글꼴: 갈무리9

모드 0.10.5 / 메뉴 패키지 0.15.5에서 게임 기본 글꼴을 Galmuri9로 변경했다. 사용자가 고운돋움의 인게임 디자인을 선호하지 않아 교체 요청했다.

- 선정 이유: 작은 크기용 한글 픽셀 글꼴이며 마인크래프트·포켓몬 게임 분위기에 적합하다고 판단했다. 비교 후보 Neo둥근모는 16px 배수 사용이 권장되므로 현재 작은 UI에서는 10px 기준 Galmuri9를 선택했다.
- 제작자 자료: https://github.com/quiple/galmuri
- 모드 0.15.1 설정은 size 9, oversample 3, shift [0,0]이다. size 10에서 채팅 영역 돌출, size 8에서 획 깨짐이 보고됐다. 중간 크기에서 글리프를 더 높은 해상도로 생성해 표시한다. 사용자가 흐릿하게 보인다고 보고해 모드 0.15.2에서 size 9를 유지하고 oversample을 1로 낮췄다. 이 설정의 실제 채팅 표시는 확인 대기 중이다.
- 라이선스: OFL 1.1 전문과 원본 TTF 포함. 출처·SHA-256은 docs/design/galmuri9-source.json.
- 게임 재시작 필요. 별도 리소스팩 선택은 필요 없다. 더 높은 우선순위의 다른 글꼴 팩에는 영향을 받을 수 있다.
- 한글 11,172자·영문·숫자, 실제 TTF 경로 변환, 소문자 리소스 경로, fallback, 칭호 아이콘 별도 폰트, JAR 파일 일치 검사 통과. 빌드·Java 68개 테스트 통과. 게임 실행·조작·실제 시각 검증은 하지 않음.

## 이전 고운돋움 작업 기록

아래는 이전 적용과 오류 수정 기록이며 현재 채택 글꼴이 아니다.

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
