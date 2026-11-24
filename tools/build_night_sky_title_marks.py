"""Requested v10 corrections. Previous PNGs are copied byte-for-byte for other species."""
import base64,csv,io,json
from PIL import Image,ImageDraw,ImageFont
import resvg_py
from build_line_title_pngs import main,BASE

OLD=BASE/'guardian-marks-v9'
OUT=BASE/'night-sky-v10'
OLD_PREVIEW={r['dex']:r for r in json.loads((OLD/'preview-data.json').read_text(encoding='utf-8'))}
OLD_BRIEFS=json.loads((OLD/'symbol-rationale.json').read_text(encoding='utf-8'))
FIXES={
 '491':('악몽의 찢어진 장막','다크라이는 달을 제외하고 날카롭게 갈라진 어둠의 장막과 악몽의 눈으로 표현. 루나아라의 달·날개 이미지와 분리함.',
 'M4 4 10 7 14 2 15 8 21 6 18 13 21 20 14 18 10 23 8 17 2 19 5 12Z M8 11 11 13 M16 11 13 13'),
 '384':('구름을 가르는 용의 비늘','레쿠쟈의 긴 몸을 그대로 그리는 대신 날개처럼 벌어진 용의 지느러미와 중심의 마름모 비늘, 아래의 구름으로 천공의 지배를 표현.',
 'M12 3 16 9 12 15 8 9Z M8 7 2 4 5 12 8 14 M16 7 22 4 19 12 16 14 M3 20Q6 15 10 19Q13 16 16 19Q19 16 22 20'),
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
    draw.text((25,20),'다크라이 · 레쿠쟈 / 기존 → 수정',font=font,fill='#edf2e8')
    for index,row in enumerate(r for r in rows if r['dex'] in FIXES):
        y=75+index*100;draw.text((25,y),row['name']+' · '+row['title'],font=font,fill='#'+row['color'])
        for x,folder in [(25,OLD),(120,OUT)]:
            im=Image.open(folder/'icons'/f"{row['dex']}.png").convert('RGBA');sheet.paste(im,(x,y+25),im)
        draw.text((90,y+38),'→',font=small,fill='#edf2e8');draw.text((190,y+35),FIXES[row['dex']][0],font=font,fill='#edf2e8')
        for x,size in [(640,24),(710,16),(770,12)]:
            im=Image.open(OUT/'icons'/f"{row['dex']}.png").convert('RGBA').resize((size,size),Image.Resampling.LANCZOS);sheet.paste(im,(x,y+30),im);draw.text((x,y+60),str(size)+'px',font=small,fill='#aabeb6')
        draw.line((25,y+89,965,y+89),fill='#293c41')
    sheet.save(OUT/'changed-marks-comparison.png')
