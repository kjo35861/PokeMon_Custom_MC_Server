"""Place completed packs in a selected instance without starting/stopping it."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import tomllib
import zipfile

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def install(jar, pack_dir, instance, delivery):
    required=json.loads((Path(__file__).resolve().parents[1]/'estate_mod/mega_compat/catalog.json').read_text(encoding='utf-8'))['required_source_sha256']
    eevee_builds = {
        'eeveemega-1.21.1-1.1.0.jar': required['eeveemega'],
        'PocketMate_Mega.jar': 'c132251daa6d90bc993440a228c92525bfb8ae8be965b7058e505e2f5e72f838',
    }
    installed_eevee = [instance/'mods'/name for name in eevee_builds if (instance/'mods'/name).exists()]
    if len(installed_eevee)!=1 or sha(installed_eevee[0])!=eevee_builds[installed_eevee[0].name]:
        raise ValueError('Unexpected EeveeMega build')
    if sha(instance/'mods/Pixelmon-1.21.1-9.4.3-universal.jar')!=required['pixelmon']:
        raise ValueError('Unexpected Pixelmon build')
    with zipfile.ZipFile(jar) as z:
        if z.testzip() is not None:raise ValueError('Compatibility JAR CRC error')
        names=z.namelist()
        if sum(n.startswith('data/pixelmon/species/') and n.endswith('.json') for n in names)!=44:
            raise ValueError('Incomplete species package')
        if any(n.startswith(('com/pixelmonmod/','com/eeveeserver/')) for n in names):
            raise ValueError('Original third-party classes must not be bundled')
        metadata=tomllib.loads(z.read('META-INF/neoforge.mods.toml').decode('utf-8'))
        own=next(m for m in metadata['mods'] if m['modId']=='pocketmate_mega_bridge')
    delivery.mkdir(parents=True,exist_ok=True)
    backup=delivery/'backups';records=[]
    def copy(src,dst,label):
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists() and sha(src)==sha(dst):
            records.append({'target':label,'sha256':sha(dst),'unchanged':True});return
        if dst.exists():
            backup.mkdir(exist_ok=True)
            stamp=datetime.now(timezone(timedelta(hours=9))).strftime('%H%M%S%f')
            shutil.copy2(dst,backup/(dst.name+'.'+stamp+'.bak'))
        temp=dst.with_name(dst.name+'.pocketmate-tmp')
        if temp.exists():raise ValueError('Temporary target already exists')
        shutil.copy2(src,temp);os.replace(temp,dst)
        if sha(src)!=sha(dst):raise ValueError('Installed hash mismatch')
        records.append({'target':label,'bytes':dst.stat().st_size,'sha256':sha(dst)})
    for src in [jar,pack_dir/'pocketmate-eeveemega-data.zip',pack_dir/'pocketmate-eeveemega-resources.zip']:
        copy(src,delivery/src.name,'delivery/'+src.name)
    # Keep one installed version of our own mod ID when its public filename changes.
    # Original EeveeMega and other mods are never selected by this migration.
    archived=[]
    for old in sorted((instance/'mods').glob('pocketmate-mega-*.jar')):
        if old.name==jar.name:continue
        if old.resolve().parent!=(instance/'mods').resolve():
            raise ValueError('Old module resolved outside selected mods directory')
        with zipfile.ZipFile(old) as oldzip:
            oldmeta=tomllib.loads(oldzip.read('META-INF/neoforge.mods.toml').decode('utf-8'))
        if not any(m['modId']=='pocketmate_mega_bridge' for m in oldmeta.get('mods',[])):continue
        backup.mkdir(exist_ok=True)
        stamp=datetime.now(timezone(timedelta(hours=9))).strftime('%H%M%S%f')
        destination=backup/(old.name+'.'+stamp+'.bak')
        try:
            old.rename(destination)
        except OSError:
            for previous,saved in reversed(archived):saved.rename(previous)
            raise
        archived.append((old,destination))
        records.append({'target':'previous_client_mod/'+old.name,'archived':True,'sha256':sha(destination)})
    try:
        copy(jar,instance/'mods'/jar.name,'client/mods/'+jar.name)
    except OSError:
        for previous,saved in reversed(archived):
            if not previous.exists():saved.rename(previous)
        raise
    worlds=[p for p in (instance/'saves').iterdir() if p.is_dir()] if (instance/'saves').exists() else []
    installed_world=False
    if len(worlds)==1:
        copy(pack_dir/'pocketmate-eeveemega-data.zip',worlds[0]/'datapacks/pocketmate-eeveemega-data.zip','single_existing_world/datapacks/pocketmate-eeveemega-data.zip')
        installed_world=True
    manifest={'version':own['version'],'display_name':own['displayName'],'client_instance':instance.parent.name,'installed_client_addon':True,
              'installed_single_existing_world_datapack':installed_world,'world_save_data_modified':False,
              'world_datapack_files_modified':installed_world,
              'restart_required':True,'runtime_tested':False,'artifacts':records}
    (delivery/'installation-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(pack_dir/'validation-report.json',delivery/'validation-report.json')
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['jar','pack-dir','instance','delivery']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();install(a.jar,a.pack_dir,a.instance,a.delivery)
