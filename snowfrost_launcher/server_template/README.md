# 포켓메이트 서버 업데이트 파일

실제 Minecraft 서버가 없어도 파일 호스팅만으로 업데이트를 시험할 수 있습니다. Python 3이 필요합니다.

1. 이 폴더의 files/mods, files/resourcepacks, files/config, files/shaderpacks 안에 배포할 파일을 넣습니다.
2. 아래 명령으로 목록을 만들고 로컬 테스트 서버를 엽니다.

```powershell
python .\build_manifest.py --version test-1 --serve
```

런처 설정의 서버 업데이트 목록 주소를 `http://127.0.0.1:18765/manifest.json`으로 저장합니다. 파일을 바꾸고 목록을 다시 생성하면 업데이트가 표시됩니다. 로컬 서버는 Ctrl+C로 종료합니다. 주소를 비우면 순정 Minecraft 1.21.1을 사용합니다.

기본 로더는 Fabric 0.20.1입니다. 모드와 맞는 다른 로더 버전이 필요하면 설치할 Fabric 로더 버전을 지정합니다. 예시 버전은 각 모드와의 호환성을 보장하지 않습니다.

```powershell
python .\build_manifest.py --version test-2 --fabric 0.16.14 --serve
```

공개 배포 때는 실제 HTTPS 호스팅 주소로 생성하고 manifest.json과 files 폴더를 함께 업로드합니다.

```powershell
python .\build_manifest.py --version 2026.11.23.1 --base-url https://YOUR-HOST/pocketmate/
```

런처에는 `https://YOUR-HOST/pocketmate/manifest.json`을 지정합니다. 이 주소는 예시입니다. HTTP는 로컬 테스트에만 허용됩니다. 친구에게 배포할 때는 EXE 옆 launcher-config.json의 updateManifestUrl에 실제 주소를 넣으세요.

파일마다 path, url, sha256, size가 필요합니다. build_manifest.py가 계산합니다. minecraftVersion은 1.21.1입니다. 각 모드의 의존성과 버전 호환성, 배포 권한을 확인하고 구성을 넣으세요. 리소스팩·셰이더팩은 게임 내 활성화가 별도로 필요합니다.

동봉한 manifest.json은 Fabric 0.20.1의 빈 서버 팩 예시이며 실제 포켓몬 모드는 포함하지 않습니다.

## Prism 연결 0.3.1

서버 주소를 지정하면 별도 Prism 서버 인스턴스에 파일을 적용하고 해당 인스턴스를 실행합니다. 로더 설정은 manifest의 loader를 따라 적용하고 Prism이 다운로드합니다. 순정 기본 인스턴스는 보존됩니다.

NeoForge 모드일 경우 정확한 호환 로더 버전을 지정합니다. 아래는 형식 예시이며 모드 호환성을 보장하지 않습니다.

```powershell
python .\build_manifest.py --version test-neo --neoforge 21.1.123 --serve
```

Fabric과 NeoForge 옵션은 동시에 지정할 수 없습니다. Minecraft 버전은 1.21.1 고정이며 Forge·Quilt는 지원하지 않습니다.

순정 서버 팩을 명시하려면 --vanilla를 사용합니다. 서버 주소 자체를 비운 경우에는 옵션과 관계없이 원래 순정 1.21.1 인스턴스를 실행합니다.

## 런처 공지와 서버 상태

실행 파일 옆의 `notices.json`을 편집하면 제목과 본문을 홈에 표시합니다. 공유하려면 이 파일을 HTTPS로 호스팅하고 같은 폴더의 `launcher-config.json`에 `noticesUrl`을 지정하세요. 실행 중에는 약 30초마다 갱신됩니다. 아래 예시는 배포 기본 공지에 포함되지 않습니다.

```json
{
  "notices": [{"title": "공지 제목", "body": "공지 본문"}],
  "maintenance": {
    "start": "2026-12-01T02:00:00+09:00",
    "end": "2026-12-01T06:00:00+09:00",
    "body": "점검 안내"
  }
}
```

점검이 없으면 `maintenance`를 `null`로 둡니다. 채널이나 게시판에서 자동으로 올리려면 운영 측 연동이 같은 JSON을 발행해야 합니다. 디스코드 봇 토큰이나 카페 로그인 정보는 배포용 런처에 넣지 않습니다.

`serverAddress`에 Java 서버의 직접 접속 주소와 포트를 지정하면 상태 응답, 현재/최대 인원 및 응답 시간을 표시합니다. Minecraft Java 상태 요청을 허용하는 서버가 필요합니다. 업데이트 manifest가 연결된 관리 인스턴스를 시작할 때 같은 주소를 Prism의 `--server`에 전달합니다.

관리 인스턴스 실행 전 `mods`의 JAR 및 `resourcepacks`의 ZIP·폴더에 배포 목록에 없는 항목이 있으면 실행을 중단합니다. 운영자는 필요한 모드와 ZIP 리소스팩을 manifest에 등록해야 합니다. 게임 중 엑스레이 판별이나 런처 전용 접속은 서버 운영 기능이 별도로 필요합니다.
