"""Verify bundled game font coverage, final JAR resources and title-font isolation."""
from pathlib import Path
import os,sys,json,hashlib,zipfile
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from fontTools.ttLib import TTFont
root=Path(__file__).resolve().parents[1];resources=root/'estate_mod/src/main/resources'
font=resources/'assets/pocketmate/font/gowun_dodum.ttf';cmap=TTFont(font).getBestCmap()
assert all(n in cmap for n in range(0xac00,0xd7a4))
assert all(ord(c) in cmap for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
p=json.loads((resources/'assets/minecraft/font/default.json').read_text())['providers']
assert p[1]['type']=='ttf' and p[1]['file']=='pocketmate:font/gowun_dodum.ttf'
assert p[-1]['id']=='minecraft:include/unifont'
assert (resources/'assets/pocketmate/font/GowunDodum-OFL.txt').is_file()
for name in ['titles','legendary_titles']:
 title=json.loads((resources/f'assets/pocketmate/font/{name}.json').read_text());assert title['providers'][0]['type']=='bitmap'
with zipfile.ZipFile(root/'estate_mod/dist/pocketmate-estates-0.10.3.jar') as z:
 for rel in ['assets/minecraft/font/default.json','assets/pocketmate/font/gowun_dodum.ttf','assets/pocketmate/font/GowunDodum-OFL.txt','assets/pocketmate/font/titles.json','assets/pocketmate/font/legendary_titles.json']:
  assert z.read(rel)==(resources/rel).read_bytes()
report={'font':'Gowun Dodum Regular','mod_version':'0.10.3','hangul_syllables_checked':11172,'latin_letters_digits':True,'fallback_references':True,'title_bitmap_fonts_preserved':True,'jar_resources_match':True,'font_sha256':hashlib.sha256(font.read_bytes()).hexdigest(),'game_tested':False,'restart_required':True}
(root/'webgui_menu/verification/gowun-dodum-font-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('11172 Hangul syllables; Latin/digits; font fallback; title font isolation; JAR resource checks passed.')
