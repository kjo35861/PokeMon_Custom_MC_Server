# 포켓메이트 런처 0.3.1 · Prism 연결

참고 이미지의 전체 배경, 왼쪽 제목과 초록색 버튼, 오른쪽 상태·안내 카드 구성을 유지한 Windows 10/11 x64용 런처입니다. .NET Framework 4.8을 사용합니다.

## 사용 방법

1. Prism Launcher를 설치합니다: https://prismlauncher.org/download/
2. Prism에서 본인 Microsoft 계정으로 로그인하고 순정 Minecraft Java 1.21.1 인스턴스를 만들어 한 번 정상 실행합니다.
3. ZIP을 풀고 PocketmateLauncher.exe를 실행합니다. 일반 설치 경로와 순정 1.21.1 인스턴스는 자동 탐색합니다.
4. 포켓메이트에서 게임 시작을 누릅니다. Prism을 미리 켤 필요는 없습니다.

Microsoft API 키, 별도 앱 등록, Client ID가 필요 없습니다. 계정 로그인과 게임 파일·Java 설치는 설치된 Prism이 처리합니다. Minecraft Java 이용 권한은 필요합니다. Prism 프로그램은 배포본에 포함하지 않습니다.

Prism이 실행 요청을 받아 게임을 시작합니다. 로그인 만료나 오류가 있으면 Prism 화면에서 안내를 확인하고 처리해야 합니다. 포켓메이트가 계정 파일이나 토큰을 읽지 않습니다. 기존 0.2.0의 직접 Microsoft 로그인 UI는 Prism 연결 설정으로 바뀌었습니다.

## 서버가 없는 경우

설정의 서버 업데이트 목록 주소를 비워 두면 선택한 **순정 Minecraft Java 1.21.1 인스턴스**를 실행합니다. 현재 배포 기본값은 주소가 비어 있으므로 이 방식입니다. 선택한 기본 인스턴스가 모드 로더를 포함하거나 버전이 다르면 실행 전에 안내합니다.

## 서버 업데이트

서버 기본 로더는 Fabric 0.20.1입니다. 서버 목록에서 loader를 생략하거나 Fabric 버전을 비우면 이 버전을 사용하며, 운영자가 명시한 다른 버전은 우선합니다. 목록 생성기도 옵션 생략 시 Fabric 0.20.1을 기록합니다. 순정 서버 팩이 필요한 경우 --vanilla를 명시하세요. 서버 주소가 없을 때의 순정 실행 방식은 그대로입니다.

업데이트 주소를 지정하면 시작 시 최신 manifest.json을 확인합니다. 변경·누락·손상된 파일이 있으면 게임 시작 버튼이 업데이트로 바뀝니다. 버튼을 누르면 목록을 다시 확인하고 다운로드·크기·SHA-256 검증을 마친 뒤 게임을 실행합니다.

업데이트 파일은 Prism 인스턴스 폴더의 minecraft/mods, resourcepacks, config, shaderpacks에 적용됩니다. 업데이트용 서버 인스턴스는 Pocketmate-Server-로 시작하는 이름으로 자동 생성하며 기본 순정 인스턴스와 분리합니다. 따라서 서버 주소를 다시 비워도 순정 게임을 실행할 수 있습니다. 서버 인스턴스에는 기본 인스턴스의 계정·월드·개인 파일을 복사하지 않습니다.

서버 manifest에서 vanilla, fabric, neoforge와 정확한 로더 버전을 지정할 수 있습니다. 서버 인스턴스의 Prism 컴포넌트 설정을 맞추고 실제 로더 다운로드와 실행은 Prism에 맡깁니다. Forge·Quilt는 지원하지 않습니다. 포켓몬 모드는 동봉하지 않으며 운영자가 1.21.1 및 로더와 호환되는 모드·의존성을 구성해야 합니다.

적용 실패 시 먼저 변경한 파일과 로더 메타데이터를 되돌립니다. 목록에서 빠진 파일은 이전에 관리한 항목만 제거하고 개인 파일은 보존합니다. 백업은 로컬 업데이트 상태 폴더에 보관합니다. 확인 실패 시 다시 확인을 표시합니다. 게임 실행 중에는 이 런처의 중복 실행·업데이트를 막습니다. Prism에서 직접 실행한 게임도 시작 직전 감지합니다.

서버 파일 호스팅은 Minecraft 게임 서버와 별개이며 HTTPS 주소를 사용합니다. 로컬 테스트는 HTTP loopback을 허용합니다. 생성과 테스트 방법은 server_template/README.md를 참고하세요. 리소스팩·셰이더팩의 게임 내 활성화 및 실제 서버 접속은 별도로 진행합니다. 서버 자동 접속 기능은 포함하지 않았습니다.

## 설정

화면의 실행 횟수 표시는 제거했습니다. 이전 설정 파일의 횟수 값은 호환성을 위해 보존하고 더 이상 증가시키지 않습니다.

톱니바퀴에서 Prism 실행 파일, Prism 데이터 폴더, 순정 인스턴스 ID, 업데이트 주소, 이름, 배경, 실행 후 최소화를 바꿀 수 있습니다. 인스턴스 ID는 화면 표시 이름이 아니라 인스턴스 폴더 이름입니다. 일반 설치 기본값:

- 실행 파일: %LOCALAPPDATA%/Programs/PrismLauncher/prismlauncher.exe
- 데이터 폴더: %APPDATA%/PrismLauncher
- 인스턴스 ID 예시: 1.21.1

포터블 Prism은 실행 파일과 데이터 폴더를 직접 확인해주세요. Prism의 사용자 지정 InstanceDir과 기존 .minecraft 인스턴스 폴더도 처리합니다. Java 21, 메모리, 계정과 Prism 창 표시 방식은 Prism에서 설정합니다.

공개 배포 기본값은 EXE 옆 launcher-config.json에서 지정합니다. 친구마다 Prism 설치와 계정 로그인·순정 인스턴스 생성이 필요합니다. 사용자별 절대 경로·계정 정보는 ZIP에 넣지 않습니다.

포켓메이트 설정은 이전 버전과 같은 %LOCALAPPDATA%/SnowfrostLauncher/settings.json에 저장합니다. Prism 업데이트 상태와 백업은 이 폴더의 prism 하위에 인스턴스별로 저장합니다. 오류는 launcher.log, 게임 실행 오류는 Prism의 게임 로그에서 확인하세요. 기존 0.2.0 게임 다운로드 캐시와 세션 파일은 삭제하지 않으며 Prism 연결에는 사용하지 않습니다.

## 검증

컴파일된 EXE로 경로 검증, 다운로드 무결성, 손상 복구, 롤백, 관리 파일 제거, Prism 경로 분리·명령 구성, Fabric/NeoForge 컴포넌트 설정을 검사했습니다. 로컬 서버를 이용해 업데이트·최신·오류·순정·설정 화면을 렌더링했습니다.

설치된 Prism과 기존 로그인 세션으로 실제 Minecraft 1.21.1 창과 리소스 초기화, 실행 프로세스 감지, 정상 종료를 확인했습니다. 실제 모드가 포함된 Fabric/NeoForge 서버 게임 플레이 검사는 하지 않았습니다. 세부 결과는 소스 verification 폴더에 있습니다.

## 빌드

Windows에 포함된 .NET Framework C# 컴파일러를 사용합니다. 별도 .NET SDK는 필요하지 않습니다.

```powershell
.\build.ps1
python .\verify_backend.py
```

src/MainWindow.xaml은 UI, Launcher.cs는 버튼과 설정, PrismBridge.cs는 Prism 연결, Services.cs는 서버 업데이트입니다. Authentication.cs와 GameInstaller.cs의 기존 직접 인증·설치 코드는 이전 기능 검사에 남아 있으며 현재 게임 시작 버튼은 PrismBridge를 사용합니다.

이전 SnowfrostLauncher.exe·ZIP 경로도 같은 새 버전으로 제공합니다. 배경 생성 기록은 assets/background-prompt.md에 있습니다.

WebGUI 사용법은 동봉한 WebGUI 사용 안내.txt를 참고하세요. WebGUI 모드나 Shift+F 보조 모드는 이번 배포본에 설치하지 않았습니다.
