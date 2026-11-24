"""Export smooth outline PNG title glyphs and a review-only Minecraft 1.21.1 pack.

No game/config/mod paths are accessed. Requires Pillow and resvg-py.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,csv,io,json,math
import resvg_py

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/design/legendary-titles'
OUT=BASE/'line-png-v3'

def render(row,color):
    # Draw smooth curves at 48px; the artwork is never quantized into pixel art.
    source=f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#{color}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="{row["path"]}"/></svg>'
    return resvg_py.svg_to_bytes(svg_string=source)

def main():
    rows=list(csv.DictReader((BASE/'catalog.tsv').open(encoding='utf-8'),delimiter='\t'))
    previous={r['dex']:r for r in json.loads((BASE/'preview-data.json').read_text(encoding='utf-8'))}
    assert len(rows)==94
    OUT.mkdir(exist_ok=True);(OUT/'icons').mkdir(exist_ok=True)
    pack=OUT/'resource-pack';assets=pack/'assets/pocketmate'
    (assets/'font').mkdir(parents=True,exist_ok=True);(assets/'textures/font').mkdir(parents=True,exist_ok=True)
    atlas=Image.new('RGBA',(48*16,48*6));preview=[];mapping=[];images={}
    for index,row in enumerate(rows):
        dex=row['dex'];png=render(row,row['color']);image=Image.open(io.BytesIO(png)).convert('RGBA');images[dex]=image
        (OUT/'icons'/f'{dex}.png').write_bytes(png);atlas.paste(image,((index%16)*48,(index//16)*48))
        item={key:previous[dex][key] for key in ['dex','name','gen','group','title','color','lightColor','motif']}
        item['dark']='data:image/png;base64,'+base64.b64encode(png).decode()
        item['light']='data:image/png;base64,'+base64.b64encode(render(row,item['lightColor'])).decode();preview.append(item)
        mapping.append({'dex':int(dex),'name':row['name'],'title':row['title'],'color':'#'+row['color'],'font':'pocketmate:legendary_titles','character':chr(0xE100+index),'codepoint':f'U+{0xE100+index:04X}','source_size':[48,48],'font_height':9,'ascent':8,'art_style':'smooth_outline_png','installed':False})
    atlas.save(assets/'textures/font/legendary_titles.png')
    chars=[''.join(chr(0xE100+i) if i<94 else '\0' for i in range(y*16,(y+1)*16)) for y in range(6)]
    font={'providers':[{'type':'bitmap','file':'pocketmate:font/legendary_titles.png','height':9,'ascent':8,'chars':chars}]}
    (assets/'font/legendary_titles.json').write_text(json.dumps(font,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    (pack/'pack.mcmeta').write_text(json.dumps({'pack':{'pack_format':34,'description':'Pocketmate smooth title icons - review draft / Minecraft 1.21.1'}},indent=2)+'\n',encoding='utf-8')
    (OUT/'glyph-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'preview-data.json').write_text(json.dumps(preview,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    examples=[]
    for row,item in zip(rows,mapping):
        examples.append('/tellraw @s '+json.dumps({'text':'','extra':[{'text':item['character'],'font':item['font'],'color':'white','bold':False},{'text':' '+row['title']+' ','font':'minecraft:default','color':'#'+row['color'],'bold':False},{'text':'포켓메이트','font':'minecraft:default','color':'white'}]},ensure_ascii=True,separators=(',',':')))
    (OUT/'tellraw-examples.txt').write_text('\n'.join(examples)+'\n',encoding='utf-8')
    normal=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',19);small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',13)
    for group,name in [('legendary','legendary-lines'),('mythical','mythical-lines')]:
        subset=[row for row in rows if row['group']==group];cols=3
        sheet=Image.new('RGB',(1200,100+math.ceil(len(subset)/cols)*96),'#111c22');draw=ImageDraw.Draw(sheet)
        draw.text((30,22),'POCKETMATE · LINE ICONS / '+('전설 71종' if group=='legendary' else '환상 23종'),font=normal,fill='#edf2e8')
        for index,row in enumerate(subset):
            x=30+(index%cols)*390;y=80+(index//cols)*96
            draw.text((x,y),row['name'],font=small,fill='#aabeb6')
            icon=images[row['dex']].resize((32,32),Image.Resampling.LANCZOS)
            sheet.paste(icon,(x,y+25),icon);draw.text((x+46,y+28),row['title'],font=normal,fill='#'+row['color']);draw.line((x,y+79,x+355,y+79),fill='#293c41')
        sheet.save(OUT/f'{name}.png')
    print('Exported 94 smooth transparent PNG icons and native bitmap-font draft. Nothing installed.')

if __name__=='__main__':main()
