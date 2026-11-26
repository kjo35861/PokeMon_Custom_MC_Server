"""Report installed Mega Boss rules and custom-form eligibility without a game run."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BIOMES = {
    'plains':'평원', 'sunflower_plains':'해바라기 평원', 'snowy_plains':'눈 덮인 평원',
    'ice_spikes':'역고드름', 'desert':'사막', 'swamp':'늪', 'mangrove_swamp':'맹그로브 늪',
    'forest':'숲', 'flower_forest':'꽃 숲', 'birch_forest':'자작나무 숲',
    'dark_forest':'어두운 숲', 'old_growth_birch_forest':'자작나무 원시림',
    'old_growth_pine_taiga':'소나무 원시 타이가', 'old_growth_spruce_taiga':'가문비나무 원시 타이가',
    'taiga':'타이가', 'snowy_taiga':'눈 덮인 타이가', 'savanna':'사바나',
    'savanna_plateau':'사바나 고원', 'windswept_hills':'바람이 세찬 언덕',
    'windswept_gravelly_hills':'바람이 세찬 자갈투성이 언덕',
    'windswept_forest':'바람이 세찬 숲', 'windswept_savanna':'바람이 세찬 사바나',
    'jungle':'정글', 'sparse_jungle':'듬성듬성한 정글', 'bamboo_jungle':'대나무 정글',
    'badlands':'악지', 'eroded_badlands':'침식된 악지', 'wooded_badlands':'나무가 우거진 악지',
    'meadow':'목초지', 'cherry_grove':'벚나무 숲', 'grove':'산림',
    'snowy_slopes':'눈 덮인 비탈', 'frozen_peaks':'얼어붙은 봉우리',
    'jagged_peaks':'뾰족한 봉우리', 'stony_peaks':'돌 봉우리',
    'river':'강', 'frozen_river':'얼어붙은 강', 'beach':'해변',
    'snowy_beach':'눈 덮인 해변', 'stony_shore':'돌 해안',
    'warm_ocean':'따뜻한 바다', 'lukewarm_ocean':'미지근한 바다',
    'deep_lukewarm_ocean':'깊고 미지근한 바다', 'ocean':'바다', 'deep_ocean':'깊은 바다',
    'cold_ocean':'차가운 바다', 'deep_cold_ocean':'깊고 차가운 바다',
    'frozen_ocean':'얼어붙은 바다', 'deep_frozen_ocean':'깊고 얼어붙은 바다',
    'mushroom_fields':'버섯 들판', 'dripstone_caves':'점적석 동굴', 'lush_caves':'무성한 동굴',
    'deep_dark':'깊은 어둠', 'the_end':'엔드 중심 섬', 'end_highlands':'엔드 고지',
    'end_midlands':'엔드 중지', 'small_end_islands':'작은 엔드 섬', 'end_barrens':'엔드 불모지',
    'nether_wastes':'네더 황무지', 'soul_sand_valley':'영혼 모래 골짜기',
    'crimson_forest':'진홍빛 숲', 'warped_forest':'뒤틀린 숲', 'basalt_deltas':'현무암 삼각주',
    'ultra_crater':'울트라 크레이터', 'ultra_deep_sea':'울트라 딥시',
    'ultra_desert':'울트라 사막', 'ultra_forest':'울트라 숲', 'ultra_jungle':'울트라 정글',
    'ultra_plant':'울트라 플랜트', 'drowned_crimson':'침수된 진홍',
    'drowned_dark':'침수된 어둠', 'drowned_warm':'침수된 온난',
}
TIMES = {'DAWN':'새벽', 'MORNING':'아침', 'DAY':'낮', 'MIDDAY':'정오',
         'AFTERNOON':'오후', 'DUSK':'해질녘', 'NIGHT':'밤', 'MIDNIGHT':'자정'}
LOCATIONS = {'Land':'육지', 'Air':'공중', 'Water':'물속', 'Underground':'지하',
             'Seafloor':'해저', 'Lava':'용암', 'Surface Water':'수면',
             'Underground Lava':'지하 용암', 'Surface Lava':'용암 표면', 'Manmade':'인공 구조물'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def spec_parts(spec):
    return {k.lower(): v for k, v in re.findall(r'(?:^|\s)([\w]+):([^\s]+)', spec)}


def safe_cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def generate(server, vanilla, output, summary):
    archives = [vanilla] + sorted((server / 'mods').glob('*.jar'))
    tags, species, spawns, lang = {}, {}, {}, {}
    available_biomes = set()
    for archive in archives:
        with zipfile.ZipFile(archive) as jar:
            for name in jar.namelist():
                if not name.endswith('.json'):
                    continue
                biome = re.fullmatch(r'data/([^/]+)/worldgen/biome/(.+)\.json', name)
                if biome:
                    available_biomes.add(biome[1] + ':' + biome[2])
                match = re.fullmatch(r'data/([^/]+)/tags/worldgen/biome/(.+)\.json', name)
                if match:
                    data = json.loads(jar.read(name))
                    key = match[1] + ':' + match[2]
                    if data.get('replace'):
                        tags[key] = []
                    tags.setdefault(key, []).extend(data.get('values', []))
                elif name.startswith('data/pixelmon/species/'):
                    data = json.loads(jar.read(name))
                    species[data['name'].lower()] = data
                elif name.startswith('data/pixelmon/spawning/'):
                    assert name not in spawns, 'Overridden spawn rules need explicit pack-priority review'
                    spawns[name] = json.loads(jar.read(name))
                elif name == 'assets/pixelmon/lang/ko_kr.json':
                    lang.update(json.loads(jar.read(name)))
    properties = dict(line.split('=', 1) for line in (server / 'server.properties').read_text('utf-8').splitlines()
                      if '=' in line and not line.lstrip().startswith('#'))
    packs = (server / properties.get('level-name', 'world') / 'datapacks').resolve()
    assert packs.is_relative_to(server.resolve()), 'World path requires separate review'
    assert not packs.exists() or not any(packs.iterdir()), 'Review world datapack priority before reporting'
    unresolved = set()

    def expand(value, stack=()):
        value = value['id'] if isinstance(value, dict) else value
        if value.startswith('#'):
            key = value[1:]
            if key in stack:
                raise ValueError('Cyclic biome tag ' + key)
            if key not in tags:
                if key.split(':')[0] in {'minecraft', 'pixelmon'}:
                    unresolved.add(key)
                return set()
            return set().union(*(expand(v, stack + (key,)) for v in tags[key])) if tags[key] else set()
        # Current server has no third-party biome mods. Keep their optional IDs
        # in the source-group column, but do not present them as available here.
        return {value} if value.startswith('minecraft:') or value in available_biomes else set()

    def biome_label(value):
        return BIOMES.get(value.split(':', 1)[1], value)

    def conditions(info):
        cond = info.get('condition', {})
        selectors = cond.get('biomes', [])
        expanded = sorted(set().union(*(expand(v) for v in selectors))) if selectors else []
        biomes = '、'.join(biome_label(v) for v in expanded) if selectors else '바이옴 제한 없음'
        if selectors and not expanded:
            biomes = '현재 설치 구성에 해당 바이옴 없음'
        times = ' / '.join(TIMES.get(t, t) for t in cond.get('times', [])) or '시간 제한 없음'
        extras = []
        weather = cond.get('weathers', [])
        if weather:
            extras.append('날씨 ' + '/'.join({'CLEAR':'맑음','RAIN':'비','STORM':'뇌우'}.get(v, v) for v in weather))
        labels = {'minY':'최소 Y', 'maxY':'최대 Y', 'minLightLevel':'최소 밝기',
                  'maxLightLevel':'최대 밝기', 'moonPhase':'달 위상', 'dimensions':'차원'}
        for key, value in cond.items():
            if key not in {'biomes', 'times', 'weathers'}:
                extras.append(labels.get(key, key) + ': ' + json.dumps(value, ensure_ascii=False))
        for key in ['anticondition', 'compositeCondition', 'conditionType', 'rarityMultipliers']:
            if info.get(key):
                extras.append(key + ': ' + json.dumps(info[key], ensure_ascii=False))
        return biomes, times, '；'.join(extras) or '없음', expanded

    def form_data(name, form):
        doc = species[name.lower()]
        return next((f for f in doc['forms'] if f['name'].lower() == form.lower()), doc['forms'][0])

    def megas(name, form):
        doc = species[name.lower()]
        stats = form_data(name, form)
        return stats.get('megas', doc['forms'][0].get('megas', []))

    def pokemon_name(name):
        return lang.get('pixelmon.' + name.lower(), name)

    dedicated, normal = [], defaultdict(list)
    for path, data in sorted(spawns.items()):
        category = path.split('/')[3]
        for index, info in enumerate(data.get('spawnInfos', [])):
            spec = spec_parts(info.get('spec', ''))
            name = spec.get('species', '')
            if not name:
                continue
            base = spec.get('form', species[name.lower()]['forms'][0]['name'])
            b, t, e, expanded = conditions(info)
            row = {'species': name, 'source_form': base, 'spec': info['spec'],
                   'biomes': b, 'times': t, 'extra': e, 'biome_ids': expanded,
                   'selectors': info.get('condition', {}).get('biomes', []),
                   'location': '/'.join(LOCATIONS.get(v, v) for v in info.get('stringLocationTypes', [])),
                   'rarity': info.get('rarity'), 'source': path, 'source_index': index,
                   'interval': info.get('interval', ''), 'boss_override': spec.get('boss')}
            if category == 'megas':
                assert info.get('interval') == 'megaBoss'
                row['mega_forms'] = megas(name, base)
                dedicated.append(row)
            elif category in {'standard', 'legendaries'}:
                normal[name.lower()].append(row)
    catalog = json.loads((ROOT / 'estate_mod/mega_compat/catalog.json').read_text('utf-8'))
    coverage = []
    for item in catalog['forms']:
        name = item['species']
        def target_for(source):
            return item['form'] if source == item['source_forms'][0] else item['form'] + '_' + source
        dedicated_hits = [r for r in dedicated if r['species'].lower() == name.lower()
                          and r['source_form'] in item['source_forms'] and target_for(r['source_form']) in r['mega_forms']]
        wild = [r for r in normal[name.lower()] if r['source_form'] in item['source_forms']
                and target_for(r['source_form']) in megas(name, r['source_form']) and not r['boss_override']]
        if wild and not dedicated_hits:
            assert any(not r['selectors'] or r['biome_ids'] for r in wild), 'No installed biome route: ' + name
        status = '전용 메가보스 + 야생 보스 전환' if dedicated_hits else '야생 보스 전환만 가능' if wild else '자연 스폰 연결 없음'
        coverage.append({'name': name, 'form': item['form'], 'source_forms': item['source_forms'],
                         'status': status, 'dedicated_rules': len(dedicated_hits), 'wild_rules': wild})
    assert not unresolved, sorted(unresolved)
    config = (server / 'config/pixelmon/spawning/boss.yml').read_text('utf-8')
    settings = dict(re.findall(r'^([\w-]+):\s*([^#\n]+)', config, flags=re.M))
    counts = Counter(row['status'] for row in coverage)
    text = ['# 현재 서버의 메가보스 스폰 조건', '',
        '2026-11-25 설치된 Pixelmon 9.4.3, 포켓메이트 메가진화 데이터, 서버 설정을 읽어 작성했다. 실제 게임에서 스폰을 발생시키거나 관찰한 결과는 아니다. 원시회귀 보스도 같은 풀이라 함께 포함했다.', '',
        '## 서버 공통 조건', '',
        f"- 전용 보스 시도 간격: `boss-spawn-ticks={settings['boss-spawn-ticks'].strip()}` (20 TPS 기준 약 {float(settings['boss-spawn-ticks'])/20:g}초, 플레이어 수 등의 배율 적용 전). 평균 시도 설정이며 일정 시간마다 확정 출현을 뜻하지 않는다.",
        f"- 전용 시도 성공 설정: `boss-spawn-chance={settings['boss-spawn-chance'].strip()}`. 적합한 플레이어·좌표·바이옴·공간 조건이 충족돼야 한다.",
        f"- 일반 야생 보스: `boss-rate={settings['boss-rate'].strip()}` → 보스 판정 기본 1/{float(settings['boss-rate']):g}. 스폰 자체의 확률이 아니다.",
        f"- `bosses-always-mega-if-possible={settings['bosses-always-mega-if-possible'].strip()}`: 원형 폼에 메가 연결이 있으면 일반 보스도 메가 등급을 선택할 수 있다.",
        '- 아래 희귀도는 후보 간 선택 가중치다. 0.3은 출현 확률 30%라는 뜻이 아니다.',
        '- 바이옴의 한글 목록은 설치 파일의 Pixelmon/바닐라 태그를 재귀적으로 펼친 결과다. Pixelmon 자체의 울트라/침수 바이옴도 포함하고, 현재 없는 BOP/Terralith 등 바이옴 모드의 선택 항목은 제외했다. 월드에 실제로 생성된 지형을 조사한 것은 아니다.',
        '- 서버 월드 datapacks 폴더는 비어 있고 모드 JAR 간 같은 스폰 경로의 중복도 없었다. 플러그인의 실시간 스폰 취소·플레이어 위치·지역 제한은 확인하지 않았다.', '',
        '## 시간 코드', '',
        '| 표기 | 월드 시간 tick (/time query daytime) |', '| --- | --- |',
        '| 새벽 DAWN | 22501–23999 또는 0–300 |', '| 낮 DAY | 0–12000 |',
        '| 오후 AFTERNOON | 6001–12000 |', '| 해질녘 DUSK | 12001–13800 |',
        '| 밤 NIGHT | 13450–23999 |',
        '', '설치 JAR의 WorldTime.SEGMENTS 기준이다. 시간대는 일부 겹치며 조건에 여러 시간이 있으면 그중 하나에 해당하면 된다. 시간 미지정은 모든 시간대다.', '',
        '## 전용 메가보스 전체 조건', '',
        f"총 {len({r['source'] for r in dedicated})}개 스폰 세트, {len(dedicated)}개 조건 행이다. X/Y/Z는 원형 종족의 메가 연결 목록에서 무작위로 선택된다. 폼마다 별도 바이옴이 정해진 것으로 해석하면 안 된다.", '',
        '| 포켓몬 | 선택 가능한 폼 | 현재 바이옴 | 시간 | 위치 | 추가 조건 | 가중치 |', '| --- | --- | --- | --- | --- | --- | --- |']
    for row in dedicated:
        forms = row['mega_forms'] or ['primal' if 'primal_' in row['source'] else '메가 연결 미발견']
        values = [pokemon_name(row['species']), ', '.join(dict.fromkeys(forms)), row['biomes'], row['times'], row['location'], row['extra'], row['rarity']]
        text.append('| ' + ' | '.join(safe_cell(v) for v in values) + ' |')
    text += ['', '다크라이의 달 위상4 조건과 뮤츠/제라오라의 최소Y90, 깜까미의 최대Y60·밝기0은 위 표의 추가 조건도 함께 충족해야 한다. 바이옴 조건이 없는 깜까미도 지하·빛·높이 조건은 유지된다.', '',
             '## 추가·보완한 45개 메가폼의 스폰 연결', '',
             '전용 메가보스 등록과 일반 야생 원형의 보스 전환을 구분한다. 일반 야생으로 출현한 원형이 보스가 될 때 메가로 바뀔 수 있어, 전용 세트가 없다는 이유만으로 출현 불가라고 판단하지 않았다.', '',
             '| 포켓몬 | 메가폼 | 진화 원형 | 판정 | 원형 스폰 조건 수 |', '| --- | --- | --- | --- | --- |']
    for row in coverage:
        text.append('| ' + ' | '.join(map(safe_cell,[pokemon_name(row['name']), row['form'], ', '.join(row['source_forms']), row['status'], len(row['wild_rules'])])) + ' |')
    text += ['', f"집계: {dict(counts)}.", '',
             '자연 스폰 연결이 없는 플라엣테는 일반 꽃색 폼과 AZ 폼이 달라 일반 플라엣테 스폰을 사용할 수 없다. 지가르데는 원형 자체의 자연 스폰 세트가 없다. 획득 후 수동 메가진화와 자연 메가보스 출현은 별개다.', '',
             '## 추가 폼의 일반 야생 보스 전환 조건', '',
             '전용 풀에 없는 폼의 원형 standard/legendaries 조건을 모두 정리했다. 전설 원형은 전설 스폰 시도 시스템까지 통과한 뒤 보스 판정이 가능하므로 아래 가중치를 메가보스 시도 확률로 읽으면 안 된다. 명시적으로 다른 boss 등급이 지정된 스폰은 이 표에서 제외했다. 팔레트가 다르면 같은 바이옴 조건이 반복될 수 있다.', '',
             '| 메가폼 | 출현 원형 spec | 분류 | 바이옴 | 시간 | 위치 | 추가 조건 | 원형 가중치 |', '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for item in coverage:
        if item['dedicated_rules']:
            continue
        for row in item['wild_rules']:
            values = [pokemon_name(item['name']) + ' ' + item['form'], row['spec'],
                      '전설' if row['interval'] == 'legendary' else '일반 야생',
                      row['biomes'], row['times'], row['location'], row['extra'], row['rarity']]
            text.append('| ' + ' | '.join(safe_cell(v) for v in values) + ' |')
    text += ['', '## 바이옴 원본 태그와 현재 설치 구성의 해석', '',
             '| 원본 선택자 | 현재 설치에서 대응하는 바이옴 |', '| --- | --- |']
    selectors = sorted({s for row in dedicated for s in row['selectors']})
    for selector in selectors:
        expanded = sorted(expand(selector))
        text.append('| ' + safe_cell(selector) + ' | ' + ('、'.join(biome_label(v) for v in expanded) or '현재 해당 바이옴 없음') + ' |')
    text += ['', '## 근거 및 적용 범위', '',
             '- 설치된 Pixelmon JAR의 data/pixelmon/spawning/megas, standard, legendaries와 biome 태그, 보완 JAR의 종족 메가 연결을 읽었다. 네이티브 SpawnInfoPokemon.createSpawnAction, AbstractHasStatsEntity.setBossTier, Stats.getRandomMegaForm, WorldTime.SEGMENTS도 정적으로 확인했다.',
             '- 공식 위키: [메가진화](https://pixelmonmod.com/wiki/Mega_Evolution), [보스](https://pixelmonmod.com/wiki/Boss), [설정](https://pixelmonmod.com/wiki/Config). 위키의 기본값과 이 서버의 사용자 설정은 다를 수 있어 표의 조건·수치는 로컬 설치 데이터가 기준이다.',
             '- 이번 요청에서는 스폰 세트·보스 설정·월드·드롭률을 변경하지 않았다. 실제 스폰 검증은 사용자가 게임에서 /checkspawns megaboss 및 해당 지역 관찰로 확인해야 한다.', '']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(text), 'utf-8')
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps({'pixelmon':'9.4.3', 'dedicated_spawn_sets':len({r['source'] for r in dedicated}),
        'dedicated_condition_rows':len(dedicated), 'catalog_forms':len(coverage), 'coverage_counts':dict(counts),
        'missing_natural_routes':[r['name'] for r in coverage if not r['dedicated_rules'] and not r['wild_rules']],
        'unresolved_biome_tags':sorted(unresolved), 'settings':{k:v.strip() for k,v in settings.items()},
        'report_sha256':digest(output), 'spawning_changed':False, 'runtime_tested':False}, ensure_ascii=False, indent=2)+'\n','utf-8')
    print(json.dumps({'dedicated_sets':len({r['source'] for r in dedicated}), 'condition_rows':len(dedicated),
                      'catalog_routes':dict(counts), 'report':str(output)},ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['server','vanilla','output','summary']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    generate(args.server, args.vanilla, args.output, args.summary)
