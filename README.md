# 포켓메이트 · Pocketmate

<img src="webgui_menu/pocketmate-mark.png" width="112" alt="포켓메이트 대표 아이콘">

친구들과 함께하는 **Minecraft Java 1.21.1 · NeoForge · Pixelmon** 서버 프로젝트입니다. Windows 런처, 인게임 WebGUI, 영지·상점·프로필 모드의 소스와 운영 기록을 보관합니다.

## 시작하기

1. [GitHub Releases의 최신 설치 마법사](https://github.com/kjo35861/PokeMon_Custom_MC_Server/releases/latest)를 실행합니다.
2. 포켓메이트 런처에서 **게임 시작**을 누릅니다. 첫 실행에서는 Prism Launcher 준비와 Microsoft 계정 로그인이 필요할 수 있습니다.
3. 서버 팩이 변경됐으면 런처가 **업데이트**를 표시합니다. 갱신을 마치면 게임을 실행합니다.
4. 서버에 입장한 뒤 **Shift+F**로 메뉴를 엽니다. 최초 닉네임은 한글로도 등록할 수 있습니다.

[런처 사용 안내](pocketmate_launcher/README.md) · [첫 접속 안내](docs/PLAYER_FIRST_RUN.md) · [인게임 명령어 목록](docs/COMMANDS.md)

## 주요 기능

| 기능 | 내용 |
| --- | --- |
| 런처·서버 팩 | 관리용 Prism 인스턴스를 분리하고 배포 목록의 경로·크기·SHA-256을 기준으로 모드와 리소스팩을 갱신합니다. |
| WebGUI | 홈, 영지관리, 상점, 임무, 프로필 편집을 제공합니다. 글자 크기와 라이트·다크 테마는 메뉴에서 조절합니다. |
| 영지 | 오버월드의 소유주 없는 청크에서 시작합니다. 기존 영지와 변으로 이어지는 청크를 지도에서 여러 개 골라 구매할 수 있습니다. 영주는 마을원·공지·홈 지점·금고를 관리합니다. |
| 성장·재화 | 영지는 레벨 0에서 시작해 최대 레벨 10, 36청크까지 확장할 수 있습니다. 정원은 영주 포함 5명입니다. 청크 구매는 영지 금고를 우선 사용하고 부족분은 영주의 개인 지갑에서 차감합니다. |
| 프로필·채팅 | 기본 프로필 아이콘은 플레이어 스킨 얼굴입니다. 착용한 칭호와 배너를 메뉴에 표시하며 채팅에는 장착한 칭호가 붙습니다. |
| 상점·운영 | 관리자 권한으로 구매·판매 품목과 가격을 관리합니다. 상점과 임무의 운영 규칙은 아래 상세 문서에서 확인할 수 있습니다. |
| Pixelmon 메가진화 | 포켓메이트 전용 메가 폼을 추가합니다. 중복 9종은 Pixelmon 기본 메가 외형을 사용합니다. 별도 Eevee 복구 ZIP은 배포 목록에서 제외했습니다. |
| 게임 글꼴·액세서리 | 게임 기본 글꼴은 Galmuri9를 사용합니다. Accessories 메뉴는 **J**로 열 수 있습니다. |

## 운영 문서

| 주제 | 문서 |
| --- | --- |
| 접속 및 설치 | [신규 플레이어 안내](docs/PLAYER_FIRST_RUN.md), [서버 설치·적용](docs/PIXELMON_SERVER_DEPLOYMENT.md), [클라이언트 팩 배포 목록](docs/client-pack/README.md) |
| 인게임 운영 | [명령어](docs/COMMANDS.md), [관리자 페이지](docs/ADMIN.md), [상점](docs/SHOP.md), [일일 임무](docs/DAILY_MISSIONS.md) |
| Pixelmon | [이벤트 연동](docs/PIXELMON_EVENT_BRIDGE.md), [메가진화 구성](docs/EEVEEMEGA_FORM_PACK.md), [메가 보스 스폰](docs/MEGA_BOSS_SPAWNS.md) |
| 구현과 검증 | [구조와 데이터 흐름](docs/ARCHITECTURE.md), [검증 자료와 확인 범위](docs/evidence/README.md), [공개·푸시 기준](docs/AUTOMATION.md) |

웹 메뉴 파일을 교체했으면 서버에서 `/webgui reload`를 실행한 뒤 메뉴를 다시 엽니다. 서버 모드 JAR를 교체했으면 정상 종료 후 `run.bat`으로 다시 시작합니다. 런처 관리 인스턴스에는 배포 목록에서 검증된 파일만 설치합니다.

## 저장소 구조와 빌드

| 경로 | 내용 |
| --- | --- |
| `pocketmate_launcher/` | Windows C#·WPF 런처, Prism 연동, 팩 갱신, 설치 마법사 |
| `webgui_menu/` | HTML·CSS·JavaScript 메뉴와 검증 스크립트 |
| `estate_mod/` | 영지·상점·프로필 모드, NeoForge 빌드, 메가진화 호환 모드 |
| `docs/`, `tools/` | 운영 문서, 날짜별 작업일지, 공개 증거, 빌드·배포 보조 도구 |

Windows, Java 21을 기준으로 저장소 루트에서 실행합니다. 로컬 Java와 Gradle 경로는 각 빌드 스크립트를 확인하세요.

```powershell
.\pocketmate_launcher\build.ps1
python pocketmate_launcher/verify_backend.py --backend-only
python estate_mod/neoforge/build.py
node webgui_menu/verification/check_appearance.cjs
python tools/prepare_evidence.py
python tools/check_publish.py
```

## 작업 기록과 검증

- [초기 개발 과정](docs/DEVELOPMENT_HISTORY.md)과 [이전 README 기록](docs/history/readme-through-2026-11-27.md)
- [11월 24일](docs/worklog/2026-11-24.md), [11월 25일](docs/worklog/2026-11-25.md), [11월 26일](docs/worklog/2026-11-26.md), [11월 27일](docs/worklog/2026-11-27.md) 작업일지
- [타사 코드·에셋·글꼴 출처](THIRD_PARTY_NOTICES.md)

작업일지는 빌드·정적 검사·모의 화면·실제 게임 테스트·사용자 확인을 구분해 기록합니다. 검증 중인 변경과 그 적용 조건도 작업일지에서 확인할 수 있습니다. 계정, 토큰, 개인 월드 및 재화 기록은 공개 저장소에 포함하지 않습니다.
