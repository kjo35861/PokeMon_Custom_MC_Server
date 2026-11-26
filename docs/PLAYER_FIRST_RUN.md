# 포켓메이트 플레이어 배포

## 현재 설치 방법

1. [최신 Windows 설치 마법사](https://github.com/kjo35861/PokeMon_Custom_MC_Server/releases/latest)에서 `Pocketmate-Setup-1.21.1.exe`를 받는다.
2. 설치 경로를 선택하고 설치한 뒤 포켓메이트 런처에서 **게임 시작**을 누른다. Prism이 없으면 런처가 설치를 진행한다. 안내가 나타나면 Microsoft 계정을 연결한다.
3. 서버 팩을 설치하거나 갱신하면 전용 Minecraft 1.21.1 / NeoForge 21.1.248 인스턴스가 시작된다. 서버 접속에는 운영 서버에 도달할 수 있는 네트워크 연결이 필요하다.
4. 게임에 접속한 뒤 **Shift+F**로 메뉴를 연다. 키를 개인 설정에서 변경했다면 설정한 키를 사용한다.

Eevee 복구 리소스팩 ZIP은 현재 배포에서 제외한다. Pixelmon 레이더 팩과 메가진화에 필요한 모드는 배포 목록을 따른다.

## 초기 설치·갱신 검증 기록

한국어, 채팅 크기·간격, Shift+F, 리소스팩, 서버 항목은 최초 생성에만 적용한다. 이후 파일 설치와 검증은 client-pack.json이 관리한다. 주소에 도달할 수 있는 네트워크 연결이 필요하다.

빈 Prism 데이터 폴더를 사용한 자동 생성, 기존 옵션 보존 및 백엔드 60개 검사 통과. ZIP의 포함 로컬 파일 해시 및 압축 무결성 확인. 별도 PC와의 접속은 미검증.


설치 연동판에서는 Prism 미설치 시 게임 시작 버튼이 WinGet의 공식 Prism 패키지 설치를 시작한다. 설치 경로를 다시 확인하고 인스턴스를 준비한 뒤 Prism을 열어 계정 추가를 안내한다. 빌드와 백엔드60개 통과. 실제 WinGet 설치 및 Microsoft 실계정 인증 미검증.


Windows 배포용 Pocketmate-Setup-1.21.1.exe는 설치 경로 선택과 기본 선택된 바탕화면 바로가기를 제공한다. 새 폴더 또는 빈 폴더를 선택한다. 격리된 사용자 지정 경로에 실제 내장 팩 추출 및 바로가기 대상·작업 경로 검증을 완료했다. 빌드 명령은 python pocketmate_launcher/build_player_setup.py <player.zip> <setup.exe> 이다.


백그라운드 시작판은 Prism 설치 완료 직후 별도로 메인 창을 열지 않고 팩 설치와 게임 실행 요청을 계속한다. 인증이나 Prism 초기 설정이 필요한 PC에서는 Prism 창이 나타날 수 있다. 런처 빌드·백엔드60개 및 설치 EXE 내부 추출·바로가기 검증 통과. 실제 새 PC 로그인 미검증.

WinGet은 콘솔 없이 실행하며 Prism 설치 중 게임 시작 버튼 안에 진행 애니메이션을 표시한다. 빌드, 백엔드60개 및 설치 EXE 추출·바로가기 검증 통과. 실제 새 PC 설치 화면 미검증.
## Windows 설치 마법사 배포

설치 마법사는 [GitHub Releases](https://github.com/kjo35861/PokeMon_Custom_MC_Server/releases/latest)에서 배포한다. 클라이언트 변경 시 새 설치 파일을 빌드하고 설치 검증, 파일 크기 및 SHA-256 확인 후 새 Release로 수동 게시한다. 같은 파일명을 사용해도 각 Release에 고유한 태그를 부여해 이전 배포를 보존한다.
