# 포켓메이트 인게임 명령어

인게임 채팅에서는 앞에 `/`를 붙입니다. 서버 콘솔에서 실행할 때는 `/`를 빼세요. `<값>`은 실제 값으로 바꿔 입력합니다. `<플레이어>`에는 접속 중인 대상의 계정명이나 등록 닉네임을 쓰면 됩니다.

## 플레이어

| 명령어 | 기능 |
| --- | --- |
| `/닉네임` | 본인의 닉네임 설정 상태를 확인합니다. |
| `/닉네임 설정 <이름>` | 처음 한 번 닉네임을 등록합니다. 한글 완성형·영문·숫자·밑줄을 사용해 2~12자로 지정할 수 있습니다. |

## 관리자

| 명령어 | 권한 | 기능 및 조건 |
| --- | --- | --- |
| `/pmprofile grant <플레이어> <종류> <항목ID>` | OP 레벨 2 이상 | 프로필 꾸미기 항목 하나를 지급합니다. 종류는 `icon`, `title`, `banner`이며 항목 ID는 Tab 자동완성으로 확인할 수 있습니다. |
| `/pmprofile grantall <플레이어> title` | OP 레벨 2 이상 | 대상에게 모든 칭호를 지급합니다. 반영을 보려면 프로필 편집을 다시 엽니다. |
| `/pmestate testcredit <플레이어> <금액>` | OP 레벨 2 이상 | 개인 지갑에 테스트 재화를 지급합니다. 서버의 `pocketmate-estates.json`에서 `freeTestMode`가 켜져 있어야 합니다. |
| `/function pocketmate_mega:stones` | 함수 실행 권한 | 포켓메이트 메가 카탈로그의 나이트를 실행한 플레이어에게 지급합니다. 콘솔에서는 `execute as <플레이어> run function pocketmate_mega:stones`로 대상 플레이어를 지정합니다. |
| `/webgui reload` | OP 레벨 2 이상 | WebGUI의 서버 설정과 메뉴 파일 목록을 갱신합니다. 웹 파일을 교체한 뒤 실행하고 메뉴를 다시 엽니다. 새 Java 명령어나 모드 JAR를 적용하려면 서버를 재시작해야 합니다. |

## Pixelmon 설정

**OP 레벨 2 이상**이 사용할 수 있습니다. 서버용 **Pocketmate Estates NeoForge 0.15.8 이상**과 Pixelmon이 필요합니다. 해당 서버에 모드를 처음 적용할 때는 `run.bat`으로 서버를 다시 시작합니다.

| 명령어 | 기능 |
| --- | --- |
| `/pixelconfig list` | 조정할 수 있는 설정과 현재값을 표시합니다. |
| `/pixelconfig get <키>` | 설정 하나의 현재값을 표시합니다. |
| `/pixelconfig set <키> <값>` | 설정을 서버에 적용하고 Pixelmon YAML에 저장합니다. |

| 키 | 값 | 설명 |
| --- | --- | --- |
| `exp-modifier` | 0~100 | 포켓몬 전투 경험치 배율. `1.5`는 1.5배입니다. |
| `legendary-spawn-chance` | 0~1 | 전설 포켓몬 스폰 시도의 성공 확률. `0.3`은 30%입니다. |
| `legendary-spawn-ticks` | 정수 1~10,000,000 | 전설 포켓몬의 평균 스폰 시도 간격에 사용하는 틱 값입니다. |
| `boss-spawn-chance` | 0~1 | 메가 보스 스폰 시도의 성공 확률입니다. |
| `boss-spawn-ticks` | 정수 1~10,000,000 | 메가 보스의 평균 스폰 시도 간격에 사용하는 틱 값입니다. |
| `spawn-ticks-player-multiplier` | 0~1 | 접속 인원에 따라 전설·메가 보스 스폰 간격을 줄이는 보정치입니다. |

20 TPS에서 20틱은 약 1초입니다. 실제 스폰 간격은 서버 부하와 Pixelmon의 무작위 간격·인원 보정에 따라 달라집니다. 틱 값을 바꾸면 다음 스폰 주기 계산부터 반영됩니다.

```text
/pixelconfig get exp-modifier
/pixelconfig set exp-modifier 1.5
/pixelconfig set legendary-spawn-chance 0.3
/pixelconfig set boss-spawn-ticks 200
```
