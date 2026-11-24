"""Build review-only title artwork. Never writes Minecraft/menu deployment files.

Optional PNG rendering uses resvg-py. Run from the repository root.
"""
from pathlib import Path
import base64,csv,html,json,math
import resvg_py

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/design/legendary-titles'
ROWS=list(csv.DictReader((OUT/'catalog.tsv').open(encoding='utf-8'),delimiter='\t'))
assert len(ROWS)==94
assert sum(r['group']=='legendary' for r in ROWS)==71
assert len({r['title'] for r in ROWS})==94
assert len({r['path'] for r in ROWS})==94
assert len({r['dex'] for r in ROWS})==94

def rgb(color):return [int(color[i:i+2],16)/255 for i in (0,2,4)]
def lum(color):return sum(v*w for v,w in zip([x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb(color)],[.2126,.7152,.0722]))
def contrast(a,b):
    x,y=sorted([lum(a),lum(b)])
    return (y+.05)/(x+.05)
def light_color(color):
    values=rgb(color)
    while contrast(''.join(f'{round(x*255):02x}' for x in values),'f5f6f0')<4.5:values=[x*.96 for x in values]
    return ''.join(f'{round(x*255):02X}' for x in values)
def svg(row,color=None,size=24):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" color="#{color or row["color"]}" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><title>{html.escape(row["name"]+" · "+row["motif"])}</title><path d="{row["path"]}"/></svg>'

(OUT/'icons').mkdir(exist_ok=True)
for row in ROWS:
    row['lightColor']=light_color(row['color'])
    row['id']='first_capture_'+row['dex']
    row['award']='server_first_successful_capture_per_species'
    row['status']='design_only_not_installed'
    (OUT/'icons'/f'{row["dex"]}.svg').write_text(svg(row),encoding='utf-8')

(OUT/'catalog.json').write_text(json.dumps({'status':'review_only','installed':False,'forms':'species-level; alternate forms share a title','sources':['https://bulbapedia.bulbagarden.net/wiki/Legendary_Pok%C3%A9mon','https://bulbapedia.bulbagarden.net/wiki/Mythical_Pok%C3%A9mon'],'titles':ROWS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def poster(rows,name,label):
    cols=3;w=1200;h=170+math.ceil(len(rows)/cols)*116
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<rect width="{w}" height="{h}" fill="#111c22"/>','<g font-family="Malgun Gothic, sans-serif">',f'<text x="38" y="42" fill="#b7d6c0" font-size="13" letter-spacing="3">POCKETMATE / FIRST ENCOUNTER</text>',f'<text x="38" y="87" fill="#edf2e8" font-size="28" font-weight="bold">{label}</text>','<text x="38" y="116" fill="#abbfb6" font-size="14">서버 최초 포획 칭호 시안 · 각 포켓몬별 1종 · 게임 미적용</text>']
    for i,row in enumerate(rows):
        x=38+(i%cols)*390;y=154+(i//cols)*116
        parts.extend([f'<path d="M{x} {y+90}H{x+356}" stroke="#293c41"/>',f'<text x="{x}" y="{y+8}" fill="#abbfb6" font-size="13">#{int(row["dex"]):04d}  {html.escape(row["name"])}</text>',f'<g transform="translate({x},{y+26}) scale(1.35)" fill="none" stroke="#{row["color"]}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="{row["path"]}"/></g>',f'<text x="{x+46}" y="{y+51}" fill="#{row["color"]}" font-size="20" font-weight="bold">{html.escape(row["title"])}</text>',f'<text x="{x+46}" y="{y+74}" fill="#91a6a0" font-size="11">{html.escape(row["motif"])}  /  #{row["color"]}</text>'])
    parts.append('</g></svg>');source=''.join(parts)
    (OUT/f'{name}.svg').write_text(source,encoding='utf-8')
    (OUT/f'{name}.png').write_bytes(resvg_py.svg_to_bytes(svg_string=source))

leg=[r for r in ROWS if r['group']=='legendary'];myth=[r for r in ROWS if r['group']=='mythical']
poster(leg[:26],'legendary-01','전설 칭호 01 · 관동 / 성도 / 호연 / 신오')
poster(leg[26:49],'legendary-02','전설 칭호 02 · 하나 / 칼로스 / 알로라')
poster(leg[49:],'legendary-03','전설 칭호 03 · 가라르 / 히스이 / 팔데아')
poster(myth,'mythical-bonus','환상 칭호 · 별도 분류 23종')

inline=[]
for row in ROWS:
    item={k:row[k] for k in ['dex','name','gen','group','title','color','lightColor','motif']}
    for theme,color in [('dark',row['color']),('light',row['lightColor'])]:
        item[theme]='data:image/png;base64,'+base64.b64encode(resvg_py.svg_to_bytes(svg_string=svg(row,color,48))).decode()
    inline.append(item)
(OUT/'preview-data.json').write_text(json.dumps(inline,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(f'Created {len(ROWS)} original title icons and four contact sheets. No game deployment.')
