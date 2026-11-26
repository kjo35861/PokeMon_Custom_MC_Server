# Pixelmon 미구현 메가진화 추가 모드 조사

조사일: 2026-11-25 (한국 시간). 공개 배포 설명과 공식 위키를 확인한 조사이며 게임 실행 검증이 아니다.

## 결론

신규 메가진화 구현물은 있다. 확인한 대표 공개 프로젝트는 Cobblemon용이며 Pixelmon에 그대로 설치하는 애드온이 아니다. Pixelmon 1.21.1 NeoForge에서 누락된 Z-A 메가진화를 일괄 추가하는 공개 배포본은 이번 검색에서 확인하지 못했다. 존재하지 않는다고 단정하지 않는다.

| 프로젝트 | 제작자 배포 페이지에서 확인한 내용 | 포켓메이트 Pixelmon에 적용 |
|---|---|---|
| Navas ZA Megas | Z-A 및 DLC 메가 45종 표기. 장크로다일, 드닐레이브, 루카리오 Z, 한카리아스 Z, 앱솔 Z 등을 명시. Cobblemon 및 Mega Showdown 필요. Minecraft 1.21.1 Fabric/NeoForge 배포 표기 | Pixelmon용이 아니므로 직접 적용 대상 아님 |
| Cobblemon: Mega Showdown | 현재 소개에서 메가 90종 이상, 메가진화와 기타 배틀 기믹 지원 표기. Minecraft 1.21.1 Fabric/NeoForge | Cobblemon용. 같은 NeoForge라도 Pixelmon 배틀·종족 데이터와 호환된다는 뜻이 아님 |

Navas 제작자 안내에는 기존 제작진에서 MSD 운영진으로 유지보수가 넘어갔다고 적혀 있다. 다른 메가 팩 및 zamegaearly와의 중복 설치 금지도 명시되어 있다. Mega Showdown 최신 소개의 90종 이상 표기와 Navas의 통합 계획을 확인했으나, 특정 최신 조합에서 Navas 별도 설치가 필요한지까지 실행 검증하지 않았다.

## Pixelmon 자체 추가분과 누락 판단의 한계

- 공식 버전 이력의 최신 항목은 9.4.3 (2026-11-24)이다. 로컬에 설치된 Pixelmon JAR 버전을 확인하거나 업데이트한 것은 아니다.
- 9.4.2에는 메가픽시, 메가치렁, 메가할비롱, 메가저리더프, 메가제라오라 추가가 명시되어 있다. 이들을 현재 Pixelmon 전체의 미구현 종류로 소개하면 안 된다.
- 공식 메가진화 목록과 종족 문서에서 장크로다일·드닐레이브의 메가 및 루카리오 Z 구현을 확인하지 못한 반면, Navas 배포 설명에는 명시되어 있다. 이는 공개 문서 비교에 따른 누락 후보 판단이며 최신 JAR 내부 데이터를 전수 대조한 확정 목록이 아니다.
- 다른 모드의 모델·데이터를 Pixelmon으로 옮기려면 해당 자산의 사용 허가와 Pixelmon 형식에 맞는 별도 구현 검토가 필요하다. 기존 배포본을 복사하면 된다는 결론은 내리지 않는다.

## 확인한 출처

- [Pixelmon 공식 버전 이력](https://pixelmonmod.com/wiki/Version_history)
- [Pixelmon 공식 메가진화 안내](https://pixelmonmod.com/wiki/Mega_Evolution)
- [Pixelmon 장크로다일 문서](https://pixelmonmod.com/wiki/Feraligatr)
- [Pixelmon 드닐레이브 문서](https://pixelmonmod.com/wiki/Baxcalibur)
- [Pixelmon 루카리오 문서](https://pixelmonmod.com/wiki/Lucario)
- [Navas 제작자 CurseForge 배포 및 포함 목록](https://www.curseforge.com/minecraft/mc-mods/navas-za-megas)
- [Navas 제작자 Modrinth 배포 및 유지보수 안내](https://modrinth.com/mod/navas-zamega)
- [Mega Showdown 제작자 Modrinth 배포](https://modrinth.com/mod/cobblemon-mega-showdown)

## 실제 수행 범위

웹 자료 조사 및 프로젝트 문서 기록만 수행했다. 게임·Prism·서버 실행/종료, 모드 설치, 월드 변경, 배틀 검증은 하지 않았다. 이 문서만으로 재시작할 필요는 없다. README에는 호환·적용 완료로 반영하지 않는다.
