# EeveeOnline 메가 모델 이미지 생성

작업일: 2026-11-25 (한국 시간). 사용자가 복구한 메가 모델을 이미지로 보고 싶다고 요청하여, 원본 BMD 형식과 텍스처를 읽어 게임 밖에서 렌더링했다. Minecraft·서버·Prism을 실행하거나 화면을 조작하지 않았다.

## 결과

- 기본색 메가 43폼의 개별 PNG 43장. 각 이미지는 앞쪽/뒤쪽 사선 두 시점을 함께 보여 준다.
- 이름을 붙인 목록 PNG 3장. 총 46개 이미지 디코딩 검사 통과.
- 이미지와 출처 manifest를 담은 `mega-model-images.zip` 생성. ZIP 전체 CRC 검사 통과.
- 출력 위치는 사용자 Downloads 아래 `eevee-mega-model-images-2026-11-25/`. 원본 모델·텍스처·렌더 이미지는 Git 저장소에 추가하지 않았다.

| 결과물 | 확인 결과 |
|---|---|
| 개별 이미지 | `individual/` 아래 43개, 각 1280×744 |
| 목록 이미지 | `mega-models-01.png`, `mega-models-02.png`, `mega-models-03.png` |
| ZIP 크기 | 15,616,277바이트 |
| ZIP SHA-256 | `60f67f9c86e3fed4a10015e886f68b1def336bf2f42927ef145b36b12bad1ce7` |
| manifest SHA-256 | `5899b8cd6f63bc7e9baab1181fa3f35a22a489d526e616176c0714e35a18dd1e` |

## 방법과 검증

- 이전에 복구한 서버 팩의 `assets/pixelmon/textures/pokemon/<종족>/all/<메가폼>/none/`에서 geometry BMD와 원본 `texture.png`를 사용했다. 스프라이트를 3D 모델 캡처로 대신하지 않았다.
- Pixelmon JAR의 `SMDModelLoader`, `Triangle.read`, `Weight.read`, `Skeleton.read`, `Mesh.createVAO`를 `javap`로 정적 분석하여 BMD reader를 작성했다. 대상 모드 코드를 실행하지 않았다.
- BMD 1·2 형식을 처리한다. 버전 2는 헤더 뒤 XZ 압축이며, 수치 big-endian/문자열 null 종료 UTF-16BE 구조를 읽었다.
- 43폼 파싱 성공, 누락/파싱 오류/남은 바이트 0. 총 geometry 삼각형 1,171,014개. 전부 재질 1개이며 같은 폴더의 `texture.png`가 존재한다.
- NumPy/Pillow 기반 CPU 렌더러로 모델 기준 좌표(Z-up), UV, 원본 기본색 텍스처를 적용했다. 별도 배경·조명과 그림자를 넣고 두 사선 시점으로 렌더링했다.
- 장크로다일에서 UV 방향과 텍스처를 비교했으며 목록 3장과 일부 앞뒤 개별 이미지를 육안 확인했다. 회전 뒤 경계 상자 검사에서 가장자리에 닿은 5폼은 중앙 배치를 보정하여 다시 렌더링했다.
- 파일별 모델/텍스처 SHA-256, 삼각형 수, 렌더 결과는 로컬 `render-manifest.json`에 기록했다.

## 한계

게임 화면 캡처가 아닌 원본 모델의 기준 자세 미리보기다. 게임의 idle 애니메이션 skinning, 셰이더, 발광·특수 이펙트, 실제 크기 비율은 재현하지 않았다. 모델별로 화면에 맞춰 크기를 조절하므로 이미지끼리 포켓몬의 실제 신장을 비교할 수 없다. 이 작업은 서버 배틀/메가진화 동작 검증이 아니며 README에 적용·플레이 검증 완료로 반영하지 않는다.

원본 캐시와 인스턴스 설정은 변경하지 않았다. 이미지 생성만 수행했으므로 재시작할 필요는 없다.
