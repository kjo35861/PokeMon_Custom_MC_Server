"""Requested v9 corrections. Previous PNGs are copied byte-for-byte for other species."""
import base64,csv,io,json
from PIL import Image,ImageDraw,ImageFont
import resvg_py
from build_line_title_pngs import main,BASE

OLD=BASE/'five-marks-v8'
OUT=BASE/'guardian-marks-v9'
OLD_PREVIEW={r['dex']:r for r in json.loads((OLD/'preview-data.json').read_text(encoding='utf-8'))}
OLD_BRIEFS=json.loads((OLD/'symbol-rationale.json').read_text(encoding='utf-8'))
FIXES={
 '773':('펼쳐지는 세 깃','실버디의 해방된 가능성을 부채꼴로 펼치는 세 깃으로 표현. 자물쇠·구속구 모티프를 완전히 제외함.',
        'M12 22C5 18 2 12 3 5L8 8 12 2 16 8 21 5C22 12 19 18 12 22Z M12 7V18 M6 10 9 17 M18 10 15 17'),
 '787':('황소 뿔 + 숲의 잎','카푸브루루의 황소와 숲의 섬지기를 큰 뿔 안의 잎으로 표현. 십자처럼 보이던 가지를 잎 모양으로 바꿈.',
        'M3 2V6Q3 11 9 11H15Q21 11 21 6V2 M12 14C5 15 7 21 12 23 17 21 19 15 12 14Z M12 15V21'),
 '788':('펼쳐진 조개','카푸느지느의 조개 껍질과 물의 섬지기를 펼쳐진 조개 그림으로 표현. 내부 겹침을 줄이고 큰 조개 윤곽을 우선함.',
        'M3 12C1 6 7 3 10 6Q12 2 14 6C19 3 25 6 21 12L15 21H9Z M12 8V18 M6 9 9 17 M18 9 15 17'),
 '891':('수련 띠를 두른 주먹','치고마의 첫 수련의 주먹을 쥔 주먹과 손목의 수련 띠로 직접 표현. 매듭만 있던 기존 추상형을 바꿈.',
        'M5 11V7Q5 4 8 6 9 2 12 5 15 2 17 6 21 4 21 8V16L17 21H8L3 16V12L7 10 10 13 M8 21V23H18V21'),
 '890':('용의 송곳니 + 독방울','무한다이노의 독룡 속성과 무한의 독룡을 굽은 용 송곳니와 분리된 독방울로 표현. 일반 무한 고리와 작은 핵의 겹침을 제거함.',
        'M4 3H15C15 12 12 20 6 23L8 12Z M19 11C16 15 15 19 19 21 23 19 22 15 19 11Z'),
 '384':('천공의 용 문장','레쿠쟈의 용과 천공 지배를 길게 흐르는 용의 곡선과 하늘의 자취로 표현. 고리·쐐기가 겹치던 이전 문장을 정리함.',
        'M8 8 5 2 11 5 17 2 16 8 20 11 15 14 11 12 M11 12C3 11 2 21 11 22H20 M16 18H22'),
 '896':('눈 덮인 빙산','블리자포스는 칭호의 발굽을 그리지 않고 빙결과 설원을 눈 덮인 빙산으로 표현. 편자·발굽 이미지를 제외함.',
        'M2 21 8 7 12 12 16 3 22 21Z M6 12 8 14 10 12 M13 10 16 12 18 10'),
 '897':('떠도는 망령','레이스포스는 칭호의 발굽을 그리지 않고 유령 속성과 그림자를 떠도는 망령으로 표현. 편자·발굽 이미지를 제외함.',
        'M6 21V10A6 6 0 0 1 18 10V21L14 18 12 21 10 18Z M9 10V13 M15 10V13'),
}

def render(row,color):
    if row['dex'] not in FIXES:
        mode='dark' if color==row['color'] else 'light'
        return base64.b64decode(OLD_PREVIEW[row['dex']][mode].split(',',1)[1])
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="-1 -1 26 26" fill="none" stroke="#{color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"><path d="{FIXES[row["dex"]][2]}"/></svg>'
    return resvg_py.svg_to_bytes(svg_string=svg)

if __name__=='__main__':
    rows=list(csv.DictReader((BASE/'catalog.tsv').open(encoding='utf-8'),delimiter='\t'))
    main(render_icon=render,output=OUT,style='guardian_concept_revision',label='CONCEPT MARKS',poster_suffix='review')
    preview=json.loads((OUT/'preview-data.json').read_text(encoding='utf-8'));briefs={}
    for item in preview:
        dex=item['dex'];briefs[dex]=dict(OLD_BRIEFS[dex])
        if dex in FIXES:briefs[dex].update(symbol_components=FIXES[dex][0],title_relation=FIXES[dex][1],path=FIXES[dex][2])
        item.update(symbol_components=briefs[dex]['symbol_components'],title_relation=briefs[dex]['title_relation'],motif=briefs[dex]['symbol_components'],revised=dex in FIXES)
    (OUT/'preview-data.json').write_text(json.dumps(preview,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (OUT/'symbol-rationale.json').write_text(json.dumps(briefs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sheet=Image.new('RGB',(1000,90+len(FIXES)*100),'#111c22');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',13)
    draw.text((25,20),'요청한 8종 / 기존 → 수정',font=font,fill='#edf2e8')
    for index,row in enumerate(r for r in rows if r['dex'] in FIXES):
        y=75+index*100;draw.text((25,y),row['name']+' · '+row['title'],font=font,fill='#'+row['color'])
        for x,folder in [(25,OLD),(120,OUT)]:
            im=Image.open(folder/'icons'/f"{row['dex']}.png").convert('RGBA');sheet.paste(im,(x,y+25),im)
        draw.text((90,y+38),'→',font=small,fill='#edf2e8');draw.text((190,y+35),FIXES[row['dex']][0],font=font,fill='#edf2e8')
        for x,size in [(640,24),(710,16),(770,12)]:
            im=Image.open(OUT/'icons'/f"{row['dex']}.png").convert('RGBA').resize((size,size),Image.Resampling.LANCZOS);sheet.paste(im,(x,y+30),im);draw.text((x,y+60),str(size)+'px',font=small,fill='#aabeb6')
        draw.line((25,y+89,965,y+89),fill='#293c41')
    sheet.save(OUT/'changed-marks-comparison.png')
