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

동봉한 manifest.json은 Fabric 0.20.1의 빈 서버 팩 예시이며 실제 포켓몬 모드는 포함하지 않습니다. 게임 서버 자동 접속 기능은 아직 포함하지 않습니다.

## Prism 연결 0.3.1

서버 주소를 지정하면 별도 Prism 서버 인스턴스에 파일을 적용하고 해당 인스턴스를 실행합니다. 로더 설정은 manifest의 loader를 따라 적용하고 Prism이 다운로드합니다. 순정 기본 인스턴스는 보존됩니다.

NeoForge 모드일 경우 정확한 호환 로더 버전을 지정합니다. 아래는 형식 예시이며 모드 호환성을 보장하지 않습니다.

```powershell
python .\build_manifest.py --version test-neo --neoforge 21.1.123 --serve
```

Fabric과 NeoForge 옵션은 동시에 지정할 수 없습니다. Minecraft 버전은 1.21.1 고정이며 Forge·Quilt는 지원하지 않습니다.

순정 서버 팩을 명시하려면 --vanilla를 사용합니다. 서버 주소 자체를 비운 경우에는 옵션과 관계없이 원래 순정 1.21.1 인스턴스를 실행합니다.
