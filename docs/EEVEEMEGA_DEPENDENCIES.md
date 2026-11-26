# EeveeMega 1.1.0 의존성 정적 분석

분석일: 2026-11-25 (한국 시간). 사용자가 제공한 15개 JAR을 읽기 전용으로 조사했다. 게임·서버·Prism·대상 모드 코드를 실행하지 않았다.

## 결론

`eeveemega-1.21.1-1.1.0.jar`의 직접 필수 구성은 Minecraft, NeoForge, Pixelmon이다. 나머지 첨부 14개 모드를 필수로 호출하거나 요구하는 관계는 확인되지 않았다. 실제 커스텀 메가진화 콘텐츠는 별도 데이터팩·리소스팩에 의존하는 구조다. 필수 모드 설치만으로 해당 서버의 메가 폼과 외형이 모두 제공되는 JAR이 아니다.

| 구성 | 확인한 요구 사항 | 근거 |
|---|---|---|
| Minecraft | 1.21.1 대상. 선언 범위 `[1.21.1,1.22)` | `META-INF/neoforge.mods.toml` |
| NeoForge | 선언 범위 `[21.1,)`, javafml loader `[4,)` | 같은 메타데이터 |
| Pixelmon | 선언 범위 `[9.3,)`, `type="required"`, `ordering="AFTER"`, `side="BOTH"` | 같은 메타데이터 및 실제 Pixelmon API 호출 |
| Java | Java 21 바이트코드 | 클래스 27개 모두 major version 65; Mixin `JAVA_21` |
| eeveemega | 서버와 클라이언트에 같은 버전을 준비하는 구성 | 공통 아이템 등록 코드 및 클라이언트 전용 메가 버튼/기술 표시 Mixin 존재. 서버만 설치한 접속 성공 여부는 실행 검증하지 않음 |
| 메가 데이터팩 | 종족의 메가 폼·스탯·스톤 매핑 등 콘텐츠 정의 필요 | `GenericMegaStone.lookup`이 `PixelmonSpecies.getAll()`과 각 폼의 `getMegaItems()`/`getMegaForms()`에서 연결 정보를 검색 |
| 메가 리소스팩 | 커스텀 외형·텍스처·아이템 표시 자산 필요 | JAR에 관련 모델·텍스처가 없고 번역 리소스만 존재 |

메타데이터의 넓은 버전 범위는 그 범위의 모든 Pixelmon·Minecraft 버전에서 호환을 검증했다는 뜻이 아니다. Pixelmon 본체 JAR과 서버 시작 로그는 이번 첨부에 없으므로 실제 설치 버전의 API/Mixin 호환성이나 기동 성공은 확정하지 않는다.

## JAR 내부에서 확인한 기능

- SHA-256: `9ed23a4b2bd8146481484b212a9b1fcf883607310d55f8378cf0847b4fc6f058`
- 크기: 57,018바이트. 클래스 27개, JSON 13개.
- `MegaStones`는 `eeveemega:mega_stone_1`부터 `mega_stone_128`까지 범용 스톤 아이템을 등록한다. 128이라는 수는 완성된 메가 포켓몬 수가 아니다.
- `EeveeMega` 생성자는 스톤·오거폰 가면·커스텀 기술 효과·명령어·이벤트를 등록한다.
- 기술 데이터 JSON 2개, 특성 구현 클래스를 가리키는 JSON 9개, 한국어 번역 1개, Mixin 설정 1개가 들어 있다. 종족/폼 데이터, 포켓몬 모델, 텍스처, 아이템 모델은 없다.
- `GenericMegaStone.lookup`은 종족 폼의 스톤 목록과 메가 폼 목록을 같은 인덱스로 비교하여 `MegaEvolution` 컴포넌트를 만든다. 매핑이 없으면 `null`을 반환한다. `verifyComponentsAfterLoad`는 이 경우 메가 컴포넌트를 채우지 않고 반환한다.
- 한국어 번역에는 장크로다일·드닐레이브·루카리오 Z 등의 스톤 이름이 있지만, 이름 문자열만으로 해당 종족의 메가 폼이 포함되었다고 판단하지 않는다.
- 공통 Mixin은 Pixelmon의 `GlobalStatusController`와 `Attack`에 연결된다. 클라이언트 Mixin은 `ClientBattleManager` 메가 버튼 판정과 `MoveButton`의 기술 표시를 보완한다. 설정의 `required=true`, `defaultRequire=1` 때문에 대상 Pixelmon 메서드가 달라진 경우 Mixin 오류 가능성이 남는다.
- 전체 클래스의 정적 참조에서 다른 Eevee 계열 모드 호출, `ModList`, `Class.forName`, `loadClass`, 자체 `CustomPacketPayload` 등록이나 `java.net` 호출은 확인되지 않았다. 동적 서버 환경까지 전수 보증하는 결과는 아니다.

## 기능별 추가 코드 확인

2026-11-25 사용자 후속 질문에 따라 특성/기술/오거폰/명령어 구현을 재확인했다. 아래는 정적 코드가 제공하는 기능이며 실제 배틀 테스트 결과가 아니다.

- 범용 스톤 128개와 Pixelmon 종족 폼의 스톤 매핑을 연결한다. 메가 폼 자체·종족별 능력치를 하드코딩한 완성 포켓몬 128종을 제공하는 구조는 아니다.
- 특성 9종: FireMane(불꽃 공격 데미지 1.5배), Eelevate(Levitate 상속과 BeastBoost 콜백 결합), SpicySpray(피격 시 공격자에게 화상 시도), Dragonize(드래곤 타입의 Ate 구현 상속), AuraGuard(접촉 공격 피해 절반), MegaSol(자신의 공격에서 쾌청 취급 및 상대 눈/모래바람 방어 보정 상쇄), PiercingDrill(접촉 공격 방어 관통·해당 관통 피해 1/4, 원래 방어 관통 기술 예외 처리), TeraShift(테라파고스 normal→terastal 및 HP 비율/특성 갱신), TeraShell(만피에서 받는 기술의 타입 상성 배율을 최대 0.5로 보정, 기존 면역·더 강한 내성 보존 및 연속 공격 처리).
- TeraShell의 번역에는 데미지 반감이라고 적혀 있으나 `scaleToHalf`는 기존 타입 상성에 대한 비율로 피해를 재조정한다. 모든 공격 피해에 단순히 0.5를 곱하는 코드라고 설명하지 않는다.
- 오거폰 우물/화덕/주춧돌 가면 아이템 3개와 소지 아이템 변경에 따른 폼 전환 코드가 있다. `OgerponMaskListener`는 해당 가면이 아니면 기본 `teal` 폼을 선택한다. 실제 폼 정의는 외부 데이터에 의존한다.
- 덩굴방망이는 풀/물/불꽃/바위 타입 전환과 클라이언트 표시 보완을 제공한다. 테라클러스터 JSON도 있으나 노말/특수/위력120 기본 기술 데이터이며 `effects`는 비어 있다. 테라파고스 폼별 특수 효과 전체를 구현했다고 보지 않는다.
- `/megastone`은 OP 권한 2 이상에서 외부 종족 데이터에 매핑된 스톤을 지급한다. `/오거폰가면 <mask>`는 가면 지급용이다. `/megacheck`, `/megadebug`, `/megaability`, `/megaweather`는 스톤 조건·종족 폼·배틀 특성·날씨 보정 진단 코드다.
- 클라이언트 메가 버튼은 든 스톤에 대응하는 메가 폼이 있는지 재확인한다. 기술 버튼의 오거폰 덩굴방망이 표시도 보완한다.

## 다른 첨부 JAR과의 관계

다음 14개 JAR의 모드 메타데이터, 클래스 상수풀 총 4,417개, 텍스트 리소스 196개를 검사했다. eeveemega 모드 의존성 선언·클래스 직접 참조·리소스 참조는 확인되지 않았다.

| 첨부 모드 | eeveemega 관련 판단 |
|---|---|
| `battleguide-c.jar` | 직접 의존 관계 미발견 |
| `eeveenetguard-1.0.3.jar` | 클라이언트 연결 오류·배틀 화면 오류 보완 Mixin. eeveemega 전용 필수 모드라는 근거 없음 |
| `eeveetcg-1.21.1-client-2.3.0.jar` | 카드 표시 기능. `mega`/`megaz` 등의 문자열은 카드 이름·폼 처리이며 eeveemega 직접 연결 아님 |
| `fishingfixclient-1.0.0.jar` | 직접 의존 관계 미발견 |
| `iris-neoforge-1.8.12+mc1.21.1.jar` | 직접 의존 관계 미발견 |
| `journeymap-neoforge-1.21.1-6.0.0-beta.54.jar` | 직접 의존 관계 미발견 |
| `ModernUI-NeoForge-1.21.1-3.12.0.2-universal.jar` | 직접 의존 관계 미발견 |
| `pixelmoncosmetic-1.21.1-client-1.0.15.jar` | 외부 장식 자산 로더. eeveemega 직접 연결 또는 메가 모델 포함 근거 없음 |
| `pixelmonlegendarytimer-1.0.0.jar` | 직접 의존 관계 미발견 |
| `pixelmontitle-client-1.0.0.jar` | 직접 의존 관계 미발견 |
| `pixelmon_disguise-client-1.0.0.jar` | 직접 의존 관계 미발견 |
| `pixelmon_submod-client.jar` | 모드·리소스팩 목록을 서버에 보고하는 일반 기능 존재. 미제공 서버 측 정책이 특정 모드를 요구하는지는 미확인 |
| `resourcepacksync-client-1.0.0.jar` | 서버의 리소스팩 정보를 수신하여 다운로드·로드하고 완료를 회신. 메가 외형 배포에 간접 활용할 수 있지만 실제 서버 팩 내용과 연결 여부는 미확인 |
| `sodium-neoforge-0.6.13+mc1.21.1.jar` | 직접 의존 관계 미발견 |

다른 14개 JAR 및 그 안의 중첩 라이브러리 JAR 15개에서 Pixelmon 종족/폼 JSON이나 포켓몬 모델 파일 경로도 확인되지 않았다. TCG 카드·전시대 자산 등은 메가 포켓몬 모델로 세지 않았다. 제공되지 않은 서버 데이터팩, 리소스팩, 플러그인, 설치 검사 정책은 이번 조사 범위 밖이다.

## 분석 방법과 적용 범위

### 후속 구현

사용자 요청으로 폼·스톤·능력치 연결과 보완 모듈을 생성하여 포켓메이트 NeoForge 테스트 인스턴스에 배치했다. 이전의 “크리에이티브 탭/데이터 없음”은 **원본 EeveeMega 단독 구성에 대한 조사**이며, 보완 모듈을 포함한 현재 배치와 구분한다. 현재 구현·출처·검사·사용자 확인 대기 범위는 `docs/EEVEEMEGA_FORM_PACK.md`와 `docs/EEVEEMEGA_FORM_CATALOG.md`에 있다.

### 후속 증상: 포켓메이트 인스턴스에서 나이트가 보이지 않음

2026-11-25 사용자 보고 후 `Pocketmate-PIXELMON-NeoForge` 인스턴스의 파일과 저장 로그를 읽기 전용으로 확인했다.

- 설치 파일은 EeveeMega 1.1.0(분석한 원본과 SHA-256 동일)과 Pixelmon 9.4.3이다.
- `latest.log`의 2026-11-25 19:12:03 기록에 `EeveeMega 로드 완료 - 메가스톤 자리 128개, 오거폰 가면 3개.`가 있다. 조사 대상 로그에서 ModLoadingException/MixinApplyError/InvalidMixinException/NoSuchMethodError/NoClassDefFoundError 표시는 없었다. 이는 기동·등록 관찰이며 배틀 전체 호환 검증은 아니다.
- 같은 로그의 모델 로딩에서 스톤 128개와 가면 3개의 아이템 모델 JSON 누락이 각각 확인된다. 해당 인스턴스의 `resourcepacks/`, `server-resource-packs/`는 비어 있고 옵션의 리소스팩 선택 목록은 `[]`다. 이전에 복구한 서버 팩은 Downloads에만 있으며 이 인스턴스에 설치된 상태가 아니다.
- 전체 EeveeMega 클래스에는 CreativeModeTab/CreativeModeTabs/BuildCreativeModeTabContentsEvent 참조가 없다. 등록한 스톤을 크리에이티브 탭에 노출하는 코드가 없다. JEI의 실제 목록 화면은 검사하지 않았다.
- 저장 로그는 싱글플레이 통합 서버 시작을 포함한다. 해당 로컬 월드의 `datapacks/`는 비어 있다. 월드 본문/인벤토리는 읽지 않았다.
- 설치된 최상위 모드 JAR의 `data/**/*.json` 15,822개를 조사했으며 `eeveemega:mega_stone_` 매핑 참조는 0개였다. 중첩 JAR 내부 데이터는 이 추가 검사에 포함하지 않았다.
- `/megastone`은 로드된 종족의 스톤 목록 중 eeveemega 네임스페이스만 모은다. 매핑이 없다면 전체 지급은 0종이 될 수 있다. 범용 아이템 등록 여부와 실제 메가 폼 연결 여부는 별개다.
- 사용자 직접 점검 명령 예시는 `/give @s eeveemega:mega_stone_18 1`. JAR 번역에서 18번은 장크로다일나이트다. 이 명령은 실행하지 않았다. 아이템을 지급받더라도 폼 매핑 없이는 메가진화 성공을 의미하지 않는다.
- 추가 잠재 결함: `MegaStoneCommand.cache`는 빈 맵도 정적으로 저장하며 자체 무효화 처리가 없다. 서버 시작/데이터팩 동기화 콜백은 `GenericMegaStone.clearCache()`만 호출한다. 향후 데이터팩 리로드 후 `/megastone` 목록이 오래 유지될 수 있으나, 현재 보고 증상의 단독 원인으로 확정하지 않았다.

이번 후속 작업은 원인 조사와 문서 기록이다. 모드 수정, 리소스팩/데이터팩 설치, 인스턴스 설정 변경, 게임/서버 실행·종료·조작은 하지 않았다. 실제 목록과 아이템 지급은 사용자 확인 대기다.

후속 조사에서 사용자가 지정한 EeveeOnline 인스턴스의 서버 리소스팩 캐시를 확인하고 복구했다. `assets/eeveemega/` 93개와 메가 포켓몬 모델·텍스처를 확보했으나, 해당 팩에는 `data/`가 없어 서버 데이터팩은 확보되지 않았다. 자세한 근거는 `docs/EEVEE_RESOURCEPACK_RECOVERY.md`에 기록했다. 아래 내용은 최초 첨부 JAR 분석 당시의 수행 범위다.

- Python ZIP/TOML·Java 클래스 상수풀 검사와 기존 JDK 21의 `javap -p -c -v`를 사용했다. 첨부 JAR을 실행하거나 수정하지 않았다.
- REA 스킬을 적용하고 CLI 6.5.0의 읽기 전용 `doctor`를 확인했다. 현재 Codex에 REA MCP 등록이 없어 일반 정적 분석 도구로 계속했다. REA Evidence ID가 생성된 분석 결과는 아니다. MCP 설정 변경이나 분석 엔진 설치는 하지 않았다.
- 원본 JAR과 전체 역어셈블 결과는 저장소에 추가하지 않았다. 문서 기록만 변경했으며 README에 설치·게임 검증 완료로 반영하지 않았다.
- 이 조사 문서 자체는 재시작이 필요 없다. 향후 실제 eeveemega 모드를 설치/교체하면 서버와 클라이언트의 모드 재시작이 필요하다. 이번 작업에서는 설치하지 않았다.
