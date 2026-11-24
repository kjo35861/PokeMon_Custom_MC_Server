"""Concept-clarity revision: replace crowded marks with recognizable small images.
Review-only. Unchanged species use the exact previous renderer.
"""
import copy,csv,json
from PIL import Image,ImageDraw,ImageFont
import resvg_py
import build_symbol_title_marks as previous
from build_line_title_pngs import main,BASE

OUT=BASE/'clear-marks-v7'
FIXES={
 '150':('유전자 실험 플라스크','뮤츠의 인공적으로 변형된 유전자와 초월한 유전자를 실험 플라스크 안의 염색체로 표현. 삼지창처럼 보이던 인장을 제거함.',
        'M9 2H15 M10 2V11L4 20Q2 23 6 23H18Q22 23 20 20L14 11V2 M10 16 14 20 M14 16 10 20'),
 '244':('분화하는 화산','앤테이의 화산·분화 개념과 화산의 포효를 화산 그림 하나로 명확하게 표현. 왕관과 내부 화염의 겹침을 없앰.',
        'M3 21 9 8 12 11 15 8 21 21Z M11 6 10 4 12 2 M6 6 4 4 M18 6 20 4'),
 '382':('거대한 바다 파도','가이오가의 대양 권능과 대양의 근원을 굽이치는 큰 파도로 표현. 원·지느러미·파도의 교차를 제거함.',
        'M2 20C8 20 7 7 15 4 21 2 24 8 19 11C21 6 16 6 14 10 12 14 18 15 22 20Z'),
 '896':('편자 + 분리된 눈 결정','블리자포스의 말·얼음과 설원을 달리는 발굽을 편자와 옆의 눈 결정으로 표현. 눈 결정을 편자 속에서 꺼내 서로 떨어뜨림.',
        'M2 6V14A6 6 0 0 0 14 14V6H11V14A3 3 0 0 1 5 14V6Z M20 2V10 M17 4 23 8 M17 8 23 4'),
 '800':('빛이 모이는 프리즘','네크로즈마의 빛·프리즘과 빛을 삼킨 프리즘을 결정과 주변의 세 빛줄기로 표현. 본체를 관통하거나 밖으로 뻗는 광선은 제거함.',
        'M12 6 19 21H5Z M12 6V21 M12 1V3 M3 8 6 11 M21 8 18 11'),
 '151':('유전자 이중 나선','뮤가 모든 유전자의 기원이라는 컨셉과 시작의 유전자를 정돈한 DNA 이중 나선으로 표현. 꼬리·점·외곽 고리의 중첩을 제거함.',
        'M7 2C19 6 19 10 12 12S5 18 17 22 M17 2C5 6 5 10 12 12S19 18 7 22 M8 5H16 M9 9H15 M9 15H15 M8 19H16'),
 '894':('큰 번개 + 두 전류 자취','레지에레키의 전기 에너지와 벼락의 거인을 한 개의 큰 번개로 표현. 작은 점 여섯 개를 제거하고 바깥에 짧은 전류 자취만 둠.',
        'M14 2 6 13H12L10 22 19 10H13Z M1 6H5 M1 18H5'),
 '1004':('곡옥 눈을 가진 불꽃 물고기','위유이의 물고기·옥 눈·불꽃과 옥빛 눈의 재앙을 물고기와 커다란 둥근 눈으로 표현. 곡옥끼리 엉킨 추상형을 없앰.',
         'M3 12C5 5 12 5 16 10L22 6V18L16 14C12 19 5 19 3 12Z M9 9A3 3 0 1 0 9 15 3 3 0 1 0 9 9 M12 7 13 3 16 7'),
 '807':('세 발톱의 발 + 분리된 번개','제라오라의 전기 발톱과 번개를 쥔 발톱을 세 개의 날카로운 발톱과 옆 번개로 표현. 평행 사선이 겹치던 낙서형을 제거함.',
        'M3 13V6L6 9 9 3 12 9 15 6V13L17 18 13 22H6L2 18Z M21 3 18 10H22L19 16'),
 '386':('은하의 나선','전체 검토 중 테오키스도 보석과 나선이 뭉개져 수정. 우주와 나선이라는 컨셉을 겹치지 않는 은하 소용돌이로 표현함.',
        'M20 8C18 1 6 1 3 9 0 17 9 24 17 20 23 17 22 8 15 7 9 6 6 13 11 16 16 19 20 13 15 11'),
}
DATA=copy.deepcopy(previous.DATA)
for dex,(components,relation,drawing) in FIXES.items():
    DATA[dex].update(symbol_components=components,title_relation=relation)

def render(row,color):
    if row['dex'] not in FIXES:return previous.render(row,color)
    drawing=FIXES[row['dex']][2]
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="-1 -1 26 26" fill="none" stroke="#{color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"><path d="{drawing}"/></svg>'
    return resvg_py.svg_to_bytes(svg_string=svg)

def comparison(rows):
    chosen=[r for r in rows if r['dex'] in FIXES]
    sheet=Image.new('RGB',(1000,80+len(chosen)*104),'#111c22');draw=ImageDraw.Draw(sheet)
    regular=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',13)
    draw.text((25,18),'컨셉·겹침 수정 비교 / 기존 → 수정',font=regular,fill='#edf2e8')
    for index,row in enumerate(chosen):
        y=70+index*104;draw.text((25,y),row['name']+' · '+row['title'],font=regular,fill='#'+row['color'])
        for x,folder in [(25,BASE/'symbol-marks-v6'),(120,OUT)]:
            icon=Image.open(folder/'icons'/f"{row['dex']}.png").convert('RGBA');sheet.paste(icon,(x,y+28),icon)
        draw.text((90,y+41),'→',font=small,fill='#edf2e8')
        draw.text((190,y+34),FIXES[row['dex']][0],font=regular,fill='#edf2e8')
        for x,size in [(640,24),(710,16),(770,12)]:
            icon=Image.open(OUT/'icons'/f"{row['dex']}.png").convert('RGBA').resize((size,size),Image.Resampling.LANCZOS);sheet.paste(icon,(x,y+32),icon);draw.text((x,y+63),str(size)+'px',font=small,fill='#aabeb6')
        draw.line((25,y+92,965,y+92),fill='#293c41')
    sheet.save(OUT/'changed-marks-comparison.png')

if __name__=='__main__':
    rows=list(csv.DictReader((BASE/'catalog.tsv').open(encoding='utf-8'),delimiter='\t'))
    main(render_icon=render,output=OUT,style='clear_concept_mark',label='CLEAR CONCEPT MARKS',poster_suffix='clear')
    preview=json.loads((OUT/'preview-data.json').read_text(encoding='utf-8'))
    for item in preview:
        item.update(DATA[item['dex']]);item['motif']=item['symbol_components'];item['revised']=item['dex'] in FIXES
    (OUT/'preview-data.json').write_text(json.dumps(preview,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    for row in rows:DATA[row['dex']].update(name=row['name'],title=row['title'],path=FIXES[row['dex']][2] if row['dex'] in FIXES else previous.OVERRIDES.get(row['dex'],row['path']))
    (OUT/'symbol-rationale.json').write_text(json.dumps(DATA,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    comparison(rows)
    print('Changed named 9 species plus Deoxys; other 84 icon images preserved.')
