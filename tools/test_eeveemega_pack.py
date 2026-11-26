"""Validate emitted species and native compatibility without starting Minecraft."""
import argparse
import copy
import json
from pathlib import Path
import unittest
import zipfile
import lzma
import struct
from build_eeveemega_pack import CATALOG, materialize_old_mappings
from pixelmon_bmd_bounds import model_bounds

class MegaContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG.read_text(encoding='utf-8'))['forms']
        cls.docs = {d['name']: d for p in (ARGS.output/'resources/data/pixelmon/species').glob('*.json')
                    for d in [json.loads(p.read_text(encoding='utf-8'))]}
        cls.forms = {name: {f['name']: f for f in d['forms']} for name, d in cls.docs.items()}

    def test_every_mapping_and_all_wrong_species_stones(self):
        contract = {}
        for row in self.catalog:
            for index, source in enumerate(row['source_forms']):
                target = row['form'] if index == 0 else row['form']+'_'+source
                contract.setdefault((row['species'], source), {})[row['stone']] = target
                f = self.forms[row['species']][target]
                self.assertEqual(f['battleStats'], row['stats'])
                self.assertEqual(f['types'], row['types'])
                self.assertEqual(f['defaultBaseForm'], source)
                self.assertFalse(any(x.startswith('eeveemega:') for x in f['megaItems']))
        all_custom = {r['stone'] for r in self.catalog if r['stone'].startswith('eeveemega:')}
        for species, forms in self.forms.items():
            for source, data in forms.items():
                actual = dict(zip(data.get('megaItems', []), data.get('megas', [])))
                expected = contract.get((species, source), {})
                for stone in all_custom:
                    self.assertEqual(actual.get(stone), expected.get(stone), (species, source, stone))

    def test_source_versions_match_pinned_hashes(self):
        catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
        report=json.loads((ARGS.output/'validation-report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['source_hashes'],catalog['required_source_sha256'])

    def test_regional_eternal_and_previous_form_reversion(self):
        self.assertEqual(self.forms['Floette']['base']['megaItems'], [])
        self.assertIn('eeveemega:mega_stone_37', self.forms['Floette']['az']['megaItems'])
        self.assertEqual(self.forms['Floette']['mega']['defaultBaseForm'], 'az')
        for source in ['curly','droopy','stretchy']:
            mapping = dict(zip(self.forms['Tatsugiri'][source]['megaItems'], self.forms['Tatsugiri'][source]['megas']))
            self.assertEqual(self.forms['Tatsugiri'][mapping['eeveemega:mega_stone_58']]['defaultBaseForm'], source)
        self.assertEqual(self.forms['Zygarde']['mega']['battleStats']['hp'], 216)
        self.assertEqual(self.forms['Zygarde']['mega_ten_percent']['defaultBaseForm'], 'ten_percent')
        self.assertEqual(self.forms['Zygarde']['complete']['megaItems'], [])

    def test_retired_stones_use_original_pixelmon_species_and_models(self):
        mapping_file = CATALOG.parent/'src/main/resources/pocketmate_native_stones.json'
        pending = set(json.loads(mapping_file.read_text(encoding='utf-8')).values())
        resources = ARGS.output/'resources'
        with zipfile.ZipFile(ARGS.pixelmon) as core:
            asset_paths = set(core.namelist())
            for path in sorted(asset_paths):
                if not path.startswith('data/pixelmon/species/') or not path.endswith('.json'):
                    continue
                doc = json.loads(core.read(path))
                base = doc['forms'][0]
                matches = pending.intersection(base.get('megaItems', []))
                if not matches:
                    continue
                self.assertFalse((resources/path).exists(), path)
                targets = dict(zip(base['megaItems'], base['megas']))
                for stone in matches:
                    form = next(f for f in doc['forms'] if f['name'] == targets[stone])
                    for gender in form['genderProperties']:
                        for palette in gender['palettes']:
                            for group in palette['models']:
                                for model in group['models']:
                                    asset = 'assets/pixelmon/textures/' + model['model'].split(':', 1)[1]
                                    self.assertIn(asset, asset_paths)
                                    self.assertFalse((resources/asset).exists(), asset)
                pending.difference_update(matches)
        self.assertFalse(pending)

    def test_preserve_native_evolutions_and_base_data(self):
        with zipfile.ZipFile(ARGS.pixelmon) as core:
            for row in self.catalog:
                original=json.loads(core.read(f"data/pixelmon/species/{row['dex']:03}_{row['slug']}.json"))
                first=original['forms'][0]
                for old in original['forms']:
                    if 'mega' in old.get('tags', []): continue
                    new=self.forms[row['species']][old['name']]
                    for key in ['battleStats','types','moves','evolutions','possibleGenders','abilities','genderProperties']:
                        if key in old: self.assertEqual(new[key],old[key],(row['species'],old['name'],key))
                    oldmap=dict(zip(old.get('megaItems',first.get('megaItems',[])),old.get('megas',first.get('megas',[]))))
                    newmap=dict(zip(new['megaItems'],new['megas']))
                    for stone,target in oldmap.items(): self.assertEqual(newmap[stone],target)
                for old in original['forms']:
                    if 'mega' in old.get('tags', []):
                        new=self.forms[row['species']][old['name']]
                        self.assertEqual(new['megaItems'],old.get('megaItems',first.get('megaItems',[])))
        for species,native,extra in [('Absol','pixelmon:absolite',48),('Garchomp','pixelmon:garchompite',50),('Lucario','pixelmon:lucarionite',49)]:
            data=self.forms[species]['base'];mapping=dict(zip(data['megaItems'],data['megas']))
            self.assertEqual(mapping[native],'mega');self.assertEqual(mapping[f'eeveemega:mega_stone_{extra}'],'megaz')

    def test_first_form_inheritance_is_frozen(self):
        fixture={'forms':[{'name':'base','megaItems':['pixelmon:old'],'megas':['mega']},
                          {'name':'regional'}, {'name':'excluded','megaItems':[],'megas':[]}]}
        materialize_old_mappings(fixture)
        fixture['forms'][0]['megaItems'].append('eeveemega:new')
        self.assertEqual(fixture['forms'][1]['megaItems'],['pixelmon:old'])
        self.assertEqual(fixture['forms'][2]['megaItems'],[])

    def test_all_generated_visual_resource_references_resolve(self):
        with zipfile.ZipFile(ARGS.pixelmon) as core:
            existing=set(core.namelist())
        def walk(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if key in ['sprite','texture','model','animation'] and isinstance(item,str) and item.startswith('pixelmon:pokemon/'):
                        path='assets/pixelmon/textures/'+item.split(':',1)[1]
                        self.assertTrue((ARGS.output/'resources'/path).is_file() or path in existing,path)
                    walk(item)
            elif isinstance(value,list):
                for item in value:walk(item)
        for row in self.catalog:
            for i,source in enumerate(row['source_forms']):
                target=row['form'] if i==0 else row['form']+'_'+source
                walk(self.forms[row['species']][target]['genderProperties'])

    def test_every_custom_model_palette_and_source_has_correct_size(self):
        report=json.loads((ARGS.output/'validation-report.json').read_text(encoding='utf-8'))
        self.assertEqual(len(report['size_audit']),34)
        self.assertEqual({r['species'] for r in report['native_size_audit']},{'Dragonite','Starmie'})
        bounds_cache={}
        checked=0
        for row in self.catalog:
            for index,source in enumerate(row['source_forms']):
                target=row['form'] if index==0 else row['form']+'_'+source
                data=self.forms[row['species']][target]
                for gender in data['genderProperties']:
                    for palette in gender['palettes']:
                        for group in palette['models']:
                            for model in group['models']:
                                path=ARGS.output/'resources/assets/pixelmon/textures'/model['model'].split(':',1)[1]
                                if not path.is_file():continue  # Preserved native geometry.
                                if path not in bounds_cache:bounds_cache[path]=model_bounds(path.read_bytes())
                                self.assertAlmostEqual(bounds_cache[path]['height']*model['scale']/16,row['height'],places=5)
                                self.assertNotEqual(model['scale'],5.0)
                                checked+=1
        self.assertEqual(len(bounds_cache),34)
        self.assertGreaterEqual(checked,68)

    def test_bmd_versions_and_stock_style_footer_omission(self):
        # Nonzero X/Y/Z bounds with no rig, one material and one triangle.
        payload=struct.pack('>hhh',0,0,1)+'skin'.encode('utf-16-be')+b'\0\0'+struct.pack('>hb',1,0)
        for x,y,z in [(0,0,0),(2,0,4),(0,3,8)]:
            payload+=struct.pack('>hffffffffb',0,x,y,z,0,0,1,0,0,0)
        for archive in [b'\1'+payload,b'\2'+lzma.compress(payload),b'\2'+lzma.compress(payload)[:-8]]:
            with self.subTest(version=archive[0],length=len(archive)):
                self.assertEqual(model_bounds(archive)['span_xyz'],[2.0,3.0,8.0])
        with self.assertRaises(ValueError):model_bounds(b'\1'+payload[:-1])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--pixelmon',type=Path,required=True)
    ARGS,remaining=p.parse_known_args()
    unittest.main(argv=['test_eeveemega_pack',*remaining])
