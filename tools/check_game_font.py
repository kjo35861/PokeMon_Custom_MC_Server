"""Verify bundled game font coverage, final JAR resources and title-font isolation."""
from pathlib import Path
import os,sys,json,hashlib,zipfile
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from fontTools.ttLib import TTFont
import re
root=Path(__file__).resolve().parents[1]
version=re.search(r"version = '([^']+)'",(root/'estate_mod/build.gradle').read_text()).group(1)
resources=root/'estate_mod/src/main/resources'
font=resources/'assets/pocketmate/font/galmuri9.ttf';cmap=TTFont(font).getBestCmap()
assert all(n in cmap for n in range(0xac00,0xd7a4))
assert all(ord(c) in cmap for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
p=json.loads((resources/'assets/minecraft/font/default.json').read_text())['providers']
assert p[1]['type']=='ttf' and p[1]['file']=='pocketmate:galmuri9.ttf'
namespace,relative=p[1]['file'].split(':',1)
resolved=resources/'assets'/namespace/'font'/relative
assert resolved.is_file() and resolved==font, 'TTF loader prepends font/; do not duplicate it'
import re
for asset in (resources/'assets').rglob('*'):
 if asset.is_file():assert re.fullmatch(r'[a-z0-9_./-]+',asset.relative_to(resources/'assets').as_posix()),asset
assert p[-1]['id']=='minecraft:include/unifont'
assert (resources/'assets/pocketmate/font/galmuri_ofl.txt').is_file()
for name in ['titles','legendary_titles']:
 title=json.loads((resources/f'assets/pocketmate/font/{name}.json').read_text());assert title['providers'][0]['type']=='bitmap'
with zipfile.ZipFile(root/f'estate_mod/dist/pocketmate-estates-{version}.jar') as z:
 for rel in ['assets/minecraft/font/default.json','assets/pocketmate/font/galmuri9.ttf','assets/pocketmate/font/galmuri_ofl.txt','assets/pocketmate/font/titles.json','assets/pocketmate/font/legendary_titles.json']:
  assert z.read(rel)==(resources/rel).read_bytes()
report={'font':'Galmuri9','mod_version':version,'hangul_syllables_checked':11172,'latin_letters_digits':True,'fallback_references':True,'title_bitmap_fonts_preserved':True,'jar_resources_match':True,'ttf_loader_resolved_path_checked':True,'all_resource_paths_lowercase':True,'font_sha256':hashlib.sha256(font.read_bytes()).hexdigest(),'game_tested':False,'restart_required':True}
(root/'webgui_menu/verification/galmuri9-font-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('11172 Hangul syllables; Latin/digits; font fallback; title font isolation; JAR resource checks passed.')
