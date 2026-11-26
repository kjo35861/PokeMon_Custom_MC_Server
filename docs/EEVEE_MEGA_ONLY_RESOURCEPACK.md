# Eevee 리소스팩에서 메가진화 자산만 유지

2026-11-25 사용자 요청으로 현재 Pocketmate Pixelmon 인스턴스에서 선택된 복구 리소스팩을 정리했다. 원본 복구 ZIP은 보존하고, 적용 중인 팩과 로컬 런처 배포 사본을 메가진화 전용 내용으로 교체했다.

## 유지 범위

- `assets/pixelmon/textures/pokemon/<종족>/<성별>/<메가폼>/...`: 폼 경로가 정확히 `mega`, `megax`, `megay`, `megaz`인 모델·애니메이션·텍스처·스프라이트 462개. 일반색·이로치와 메가폼 전용 스킨을 모두 유지했다. 종족명에 mega가 포함된 일반 메가니움 등은 이 조건에 포함되지 않는다.
- `assets/eeveemega/models/item/mega_stone_<번호>.json`과 대응 PNG 86개. 원본에 있던 43개 스톤의 모델/아이콘을 그대로 유지했다. 이 숫자는 실제 연결된 스톤·폼 개수와 구분한다.
- 한국어 번역은 메가스톤 키 6개와 `pixelmon.generic.form.megaz` 한 개만 유지했다. 일반 스킨·메뉴·일반 포켓몬 폼 번역은 제거했다.
- Minecraft 1.21.1 리소스팩 메타데이터만 새로 작성했다. 기존 ItemsAdder 오버레이 선언은 제거했다.

기본 UI, 폰트, 셰이더, 사운드, 일반 아이템/블록, 일반 포켓몬 스킨, HUD, 칭호, 장식, TCG, 오거폰 가면은 포함하지 않는다. 가챠 메가스톤 상자처럼 이름만 메가를 포함한 서버 상점 UI 자산도 제외했다. `assets/minecraft/` 파일은 0개이며 네임스페이스는 `pixelmon`, `eeveemega`만 남는다. 메가스톤 모델의 기본 `item/generated` 부모는 Minecraft 기본 모델을 참조하고 바꾸지 않는다.

## 결과와 검증

| 항목 | 결과 |
| --- | --- |
| 원본 엔트리 | 5,445개 |
| 정리 후 엔트리 | 551개: 자산548 + 번역2 + 메타데이터1 |
| 제거된 파일 경로 | 4,894개 |
| 크기 | 778,172,765 → 182,689,572바이트 |
| 정리본 SHA-256 | `415e80b6aad1280f7cc97f6aed00db3bfa0ec43f101acfdfd839b4d23ff112fe` |
| 유지 자산 비교 | 548개 모두 원본과 바이트 동일 |
| 메가 보완 모드 자산 비교 | 내장 포켓몬 자산263개 모두 포함·바이트 동일 |
| ZIP 및 아이템 참조 | 전체 CRC 통과, 스톤 텍스처 참조 모두 존재 |
| 범위 제한 | Minecraft 네임스페이스 및 GUI/폰트/셰이더/사운드 경로 0개 |
| 런처 | 실제 CheckLocal/VerifyApprovedContent 통과, 다운로드·제거 예정0개 |

검증 요약은 `docs/evidence/reports/eeveemega/mega-only-resourcepack-static.json`, 재현 코드는 `tools/filter_eevee_mega_resources.py`다. JAR·ZIP·개별 텍스처/모델은 저장소에 포함하지 않는다. 폼 데이터·능력치·모드 코드는 이번에 변경하지 않았다.

## 배치와 적용

- 현재 인스턴스의 `resourcepacks/eevee-server-resourcepack-recovered.zip`을 내용 교체했다. 선택된 파일명을 유지하여 `options.txt`를 수정하지 않았다.
- 로컬 ClientPack 런처의 배포 사본과 등록 SHA-256/크기/팩 버전도 함께 갱신했다. 다른 승인 항목은 유지했다.
- 별도 배포본: Downloads의 `pocketmate-eeveemega-compat-2026-11-25/PocketMate_Mega_Resources.zip`.
- 원본 및 이전 런처 목록 백업: `%LOCALAPPDATA%/PocketmateServerBackups/2026-11-25-mega-only-resourcepack`. Downloads의 기존 원본 복구 ZIP도 그대로 보존했다.

현재 인스턴스의 서버 리소스팩 캐시는 비어 있고 로컬 서버의 강제 리소스팩 설정도 비어 있음을 확인했다. 다른 인스턴스와 EeveeOnline 원본 캐시는 수정하지 않았다.

게임 실행 중이라면 사용자가 F3+T로 리소스를 다시 불러오거나 게임을 재시작해야 메모리에 남은 이전 UI 자산이 사라진다. 서버 파일은 변경하지 않아 서버 재시작은 필요하지 않다. 게임/Prism/서버 실행·종료·화면 조작은 수행하지 않았고, 실제 UI 복원 및 메가 모델 렌더링은 사용자 확인 대기다.
