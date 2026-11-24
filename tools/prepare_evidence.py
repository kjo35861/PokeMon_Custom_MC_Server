"""Publish selected evidence with local paths masked. Output is deterministic.
Missing local originals on another checkout never remove archived evidence.
"""
from pathlib import Path
import argparse,hashlib,json,re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence'
MANIFEST=OUT/'manifest.json'

def scrub(text):
    for original,label in [(str(ROOT),'<WORKSPACE>'),(str(Path.home()),'<USERPROFILE>')]:
        for spelling in {original,original.replace('\\','/'),original.replace('\\','\\\\')}:
            text=text.replace(spelling,label)
    return text

def clean(value):
    if isinstance(value,dict):
        result={}
        for key,item in value.items():
            if re.sub(r'[^a-z]','',key.lower()) in {'accesstoken','refreshtoken','idtoken','password','clientsecret','authorization','cookie','devicecode','sessiontoken','xbltoken','xststoken','minecrafttoken'} and isinstance(item,str) and item:
                result[key]='<REDACTED>'
            else:result[key]=clean(item)
        return result
    if isinstance(value,list):return [clean(item) for item in value]
    return scrub(value) if isinstance(value,str) else value

def candidates():
    for folder in ['webgui_menu','snowfrost_launcher']:
        for source in sorted((ROOT/folder/'verification').glob('*.json')):
            if source.name.endswith('.state.json'):continue
            yield source,f'reports/{folder}/{source.name}','historical-or-current-report'
    for source in sorted((ROOT/'estate_mod/verification/test-results/test').glob('TEST-*.xml')):
        yield source,f'reports/estate_mod/{source.name}','junit-result'
    screenshots={
        'webgui_menu/verification/home-block-art-dark.png':'home-block-art-v0.18.1-dark-mock.png',
        'webgui_menu/verification/home-block-art-light.png':'home-block-art-v0.18.1-light-mock.png',
        'webgui_menu/verification/shop-foundation-dark.png':'shop-v0.18-dark-mock.png',
        'webgui_menu/verification/shop-foundation-light.png':'shop-v0.18-light-mock.png',
        'webgui_menu/verification/docked-profile-missions-dark.png':'menu-v0.17-docked-profile-dark-mock.png',
        'webgui_menu/verification/docked-profile-missions-light.png':'menu-v0.17-docked-profile-light-mock.png',
        'webgui_menu/verification/daily-missions-rules-dark.png':'daily-missions-rules-dark-mock.png',
        'webgui_menu/verification/daily-missions-rules-light.png':'daily-missions-rules-light-mock.png',
        'webgui_menu/verification/daily-missions-dark.png':'daily-missions-dark-mock.png',
        'webgui_menu/verification/daily-missions-light.png':'daily-missions-light-mock.png',
        'webgui_menu/verification/redesign-preview.png':'historical-menu-redesign.png',
        'webgui_menu/verification/estate-plaza-v0.8.png':'historical-estate-plaza.png',
        'webgui_menu/verification/estate-management.png':'historical-estate-map-mock.png',
        'webgui_menu/verification/estate-vault.png':'historical-estate-treasury.png',
        'webgui_menu/verification/profile-studio.png':'historical-profile-studio.png',
        'snowfrost_launcher/verification/current-prism-preview.png':'historical-launcher-prism-0.3.0.png',
    }
    for original,name in screenshots.items():
        source=ROOT/original
        if source.exists():yield source,'screenshots/'+name,('headless-mock-ui-screenshot' if name.startswith(('daily-missions-','menu-v0.17-','shop-v0.18-','home-block-art-')) else 'historical-ui-screenshot')
    for name in ['brand-final-prompt.txt','brand-universal-prompt.txt']:
        source=ROOT/'webgui_menu/verification'/name
        if source.exists():yield source,'artwork/'+name,'image-generation-prompt'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    existing=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {'format':1,'entries':{}}
    allowed=('reports/webgui_menu/','reports/snowfrost_launcher/','reports/estate_mod/','screenshots/','artwork/')
    entries={key:value for key,value in existing['entries'].items() if key.startswith(allowed)};changed=[]
    for source,relative,kind in candidates():
        original=source.read_bytes()
        if source.suffix=='.json':
            public=(json.dumps(clean(json.loads(original.decode('utf-8-sig'))),ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        elif source.suffix in {'.xml','.txt'}:public=scrub(original.decode('utf-8-sig')).replace('\r\n','\n').replace('\r','\n').encode('utf-8')
        else:public=original
        target=OUT/relative
        if not target.exists() or target.read_bytes()!=public:
            changed.append(relative)
            if not args.check:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(public)
        entries[relative]={'source':source.relative_to(ROOT).as_posix(),'kind':kind,'source_sha256':hashlib.sha256(original).hexdigest(),'published_sha256':hashlib.sha256(public).hexdigest(),'bytes':len(public),'sanitized':original!=public}
    manifest=(json.dumps({'format':1,'entries':dict(sorted(entries.items()))},ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if not MANIFEST.exists() or MANIFEST.read_bytes()!=manifest:
        changed.append('manifest.json')
        if not args.check:OUT.mkdir(parents=True,exist_ok=True);MANIFEST.write_bytes(manifest)
    print(f'Evidence: {len(entries)} archived entries; {len(changed)} changed outputs.')
    if args.check and changed:raise SystemExit(2)

if __name__=='__main__':main()
