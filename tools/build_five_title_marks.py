"""Five requested concept corrections, preserving all other v7 PNGs."""
import copy,csv,json
from PIL import Image,ImageDraw,ImageFont
import resvg_py
import build_clear_title_marks as previous
from build_line_title_pngs import main,BASE

OUT=BASE/'five-marks-v8'
FIXES={
 '151':('기원의 세포 + 유전자 한 가닥','뮤는 생명의 기원인 세포 안에 유전자 한 가닥을 두어 시작의 유전자를 표현. 겹친 이중 나선과 작은 가로선을 제거함.',
        'M12 3A9 9 0 1 0 12 21 9 9 0 1 0 12 3 M11 7C6 9 18 15 13 17 M15 7H15.1'),
 '385':('소원의 별 + 떨어지는 별빛','지라치는 별에 건 소원을 한 개의 별과 짧은 별빛 궤적으로 표현. 별 꼭짓점에 걸려 겹치던 세 끈을 없앰.',
        'M13 3 16 9 22 10 18 15 19 22 13 18 7 22 8 15 4 10 10 9Z M2 3 5 6 M1 8H3'),
 '1016':('부드러운 깃털 + 독 사슬 고리','기로치는 유혹을 떠올리는 한 장의 깃털과 독 사슬의 고리를 분리해 사슬에 핀 유혹을 표현. 깃의 잔가지와 교차 매듭을 제거함.',
         'M6 19C1 9 8 2 17 3 20 10 15 17 6 19Z M3 22 14 9 M18 17A3 3 0 1 0 18 23 3 3 0 1 0 18 17'),
 '649':('고대 포신 + 작은 조준점','게노세크트는 등에 달린 포를 큰 포신으로 표현하고 조준점은 바깥으로 분리함. 곤충 마디·받침·포의 겹침을 없앰.',
        'M3 7H17V13H3Z M17 8H21V12H17 M7 13 5 21H15L13 13 M7 18H13 M21 2V5 M19 3H23'),
 '893':('덩굴이 감긴 손','자루도는 손목을 감은 덩굴과 손가락이 구분되는 손으로 밀림의 덩굴손을 표현. 서로 가로지르던 추상 매듭을 없앰.',
        'M7 20 4 13Q3 10 6 11L9 14V6Q9 3 11 5V12 M11 7Q12 4 14 6V12 M14 8Q16 5 17 8V13 M17 10Q20 8 20 12V17L17 21 M7 21Q12 18 18 21 M8 23Q12 21 17 23'),
}
DATA=copy.deepcopy(previous.DATA)
for dex,(components,relation,drawing) in FIXES.items():DATA[dex].update(symbol_components=components,title_relation=relation)

def render(row,color):
    if row['dex'] not in FIXES:return previous.render(row,color)
    source=f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="-1 -1 26 26" fill="none" stroke="#{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="{FIXES[row["dex"]][2]}"/></svg>'
    return resvg_py.svg_to_bytes(svg_string=source)

if __name__=='__main__':
    rows=list(csv.DictReader((BASE/'catalog.tsv').open(encoding='utf-8'),delimiter='\t'))
    main(render_icon=render,output=OUT,style='five_concept_corrections',label='CONCEPT MARKS',poster_suffix='review')
    old=json.loads((BASE/'clear-marks-v7/symbol-rationale.json').read_text(encoding='utf-8'))
    preview=json.loads((OUT/'preview-data.json').read_text(encoding='utf-8'))
    for item in preview:
        item.update(DATA[item['dex']]);item['motif']=item['symbol_components'];item['revised']=item['dex'] in FIXES
    (OUT/'preview-data.json').write_text(json.dumps(preview,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    for row in rows:DATA[row['dex']].update(name=row['name'],title=row['title'],path=FIXES[row['dex']][2] if row['dex'] in FIXES else old[row['dex']]['path'])
    (OUT/'symbol-rationale.json').write_text(json.dumps(DATA,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sheet=Image.new('RGB',(1000,590),'#111c22');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',13)
    draw.text((25,20),'요청한 5종 / 기존 → 수정',font=font,fill='#edf2e8')
    for index,row in enumerate(r for r in rows if r['dex'] in FIXES):
        y=75+index*100;draw.text((25,y),row['name']+' · '+row['title'],font=font,fill='#'+row['color'])
        for x,folder in [(25,BASE/'clear-marks-v7'),(120,OUT)]:
            im=Image.open(folder/'icons'/f"{row['dex']}.png").convert('RGBA');sheet.paste(im,(x,y+25),im)
        draw.text((90,y+38),'→',font=small,fill='#edf2e8');draw.text((190,y+35),FIXES[row['dex']][0],font=font,fill='#edf2e8')
        for x,size in [(640,24),(710,16),(770,12)]:
            im=Image.open(OUT/'icons'/f"{row['dex']}.png").convert('RGBA').resize((size,size),Image.Resampling.LANCZOS);sheet.paste(im,(x,y+30),im);draw.text((x,y+60),str(size)+'px',font=small,fill='#aabeb6')
        draw.line((25,y+89,965,y+89),fill='#293c41')
    sheet.save(OUT/'five-marks-comparison.png')
