# 게임 실행 후 마인크래프트 창 활성화

게임 JVM이 검출된 뒤 해당 프로세스의 마인크래프트 창이 준비되면 앞으로 가져온다. `실행 후 런처 최소화` 설정은 창 활성화 시도 이후 적용한다. 새로 실행한 게임과 실행 중인 게임을 다시 연결하는 분기에 같은 처리를 사용한다.

- 실행 대상 PID에 속한, 화면에 표시되는 소유자 없는 GLFW 창이면서 제목에 Minecraft가 있는 창만 선택한다.
- 최대 약 2분 동안 창 생성을 기다린다. 최소화된 게임 창은 복원하며, 위치와 크기는 변경하지 않는다.
- 활성화가 성공하면 더 이상 개입하지 않는다. 실패 시 최대 3회 시도한 뒤 작업 표시줄 알림을 보낸다. 항상 위 고정은 사용하지 않는다.
- 취소·게임 종료 시 중단하고, 로딩 중 교체된 창 핸들은 활성화 직전에 다시 확인한다.

Windows의 전경 창 제한에 따라 활성화 요청이 거절될 수 있다. 구현은 [SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow), [AllowSetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-allowsetforegroundwindow), [ShowWindowAsync](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindowasync) 공식 문서를 참고했다.

## 검증 및 적용

2026-11-26에 .NET Framework 빌드와 백엔드 60개 검사를 통과했다. 이 중 창 관련 7개 검사는 콜백으로 지연 생성·대상 선택·실패 제한·종료·취소·창 교체를 모의 검증한다. 실제 마인크래프트·Prism 실행이나 게임 창 조작은 하지 않았다. 실제 게임 실행 후 전경 전환은 사용자 확인 대기다.

배포 EXE SHA-256: `abdd192e576ddc95c90e95fcf235318c5b873e76aaa3883eddf9524d0625b999`.

기존 클라이언트 폴더에 `PocketmateLauncher-ClientPack-Foreground.exe`를 배치했다. 같은 폴더의 설정과 팩 목록을 그대로 이용한다. 실행 중이라 잠긴 원래 `PocketmateLauncher-ClientPack.exe`는 클라이언트가 종료되면 교체하도록 로컬 업데이트 도우미를 대기시켰다. 도우미는 프로세스를 종료하거나 실행하지 않으며, 원본을 백업하고 해시가 달라졌으면 덮어쓰기를 중단한다. 대기 한도는 24시간이다.

새 기능은 클라이언트를 닫고 다시 열면 적용된다. 서버·모드 변경이나 서버 재시작은 필요 없다. 기존 설정·팩 목록은 수정하지 않았다.
