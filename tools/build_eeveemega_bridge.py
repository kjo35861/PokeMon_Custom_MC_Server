"""Compile only the compatibility mod, outside OneDrive; never launch Minecraft."""
import argparse
import os
from pathlib import Path
import json
import re
import shutil
import subprocess
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]

def prepare_stone_namespace(source, destination, recovered_pack):
    shutil.copytree(source, destination, dirs_exist_ok=False)
    legacy = destination / 'assets/eeveemega'
    branded = destination / 'assets/pocketmate_mega'
    # The archived pack contains the original inventory art for these slots.
    with ZipFile(recovered_pack) as archive:
        for number in range(54, 59):
            item = f'mega_stone_{number}'
            model_path = f'assets/eeveemega/models/item/{item}.json'
            model = json.loads(archive.read(model_path))
            texture_ns, texture_path = model['textures']['layer0'].split(':', 1)
            texture = f'assets/{texture_ns}/textures/{texture_path}.png'
            for path in (model_path, texture):
                target = destination / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(path))
    for model in (legacy / 'models/item').glob('mega_stone_*.json'):
        folder = branded / 'models/item'
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(model, folder / model.name)
    for language in (legacy / 'lang').glob('*.json'):
        translations = json.loads(language.read_text(encoding='utf-8'))
        names = {
            key.replace('item.eeveemega.', 'item.pocketmate_mega.', 1): value
            for key, value in translations.items()
            if re.fullmatch(r'item\.eeveemega\.mega_stone_\d+', key)
        }
        if names:
            target = branded / 'lang' / language.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(names, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for path in [destination / 'pocketmate_mega_catalog.json', *(destination / 'data').rglob('*.json')]:
        if not path.is_file():
            continue
        original = path.read_bytes()
        updated = re.sub(rb'eeveemega:(mega_stone_\d+)(?![a-z0-9_./-])', rb'pocketmate_mega:\1', original)
        if updated != original:
            path.write_bytes(updated)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pixelmon',type=Path,required=True)
    p.add_argument('--eeveemega',type=Path,required=True)
    p.add_argument('--generated',type=Path,required=True)
    p.add_argument('--recovered-pack',type=Path,required=True)
    p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--java-home',type=Path,default=Path('C:/Program Files/Java/jdk-21.0.12'))
    p.add_argument('--gradle-home',type=Path,default=Path(os.environ.get('LOCALAPPDATA','.'))/'PocketmateEstateTools/gradle-8.12.1')
    args=p.parse_args()
    source=ROOT/'estate_mod/mega_compat';args.stage.mkdir(parents=True,exist_ok=True)
    for n in ['build.gradle','settings.gradle','gradle.properties']:shutil.copy2(source/n,args.stage/n)
    shutil.copytree(source/'src',args.stage/'src',dirs_exist_ok=True)
    env=os.environ.copy();env['JAVA_HOME']=str(args.java_home)
    env['PATH']=str(args.java_home/'bin')+os.pathsep+env['PATH']
    env['GRADLE_USER_HOME']=str(args.gradle_home.parent/'gradle-cache')
    import tempfile
    with tempfile.TemporaryDirectory(prefix='pocketmate-stone-namespace-', dir=args.stage) as temp:
        generated = Path(temp) / 'resources'
        prepare_stone_namespace(args.generated.resolve(), generated, args.recovered_pack.resolve())
        cmd=[str(args.gradle_home/'bin/gradle.bat'),'build','--console=plain','--no-daemon',
             '-PpixelmonJar='+str(args.pixelmon.resolve()),'-PeeveemegaJar='+str(args.eeveemega.resolve()),
             '-PgeneratedResources='+str(generated.resolve())]
        subprocess.run(cmd,cwd=args.stage,env=env,check=True)
    for jar in (args.stage/'build/libs').glob('*.jar'):print(jar)

if __name__=='__main__':main()
