"""Check Git publication files, reporting paths/rules without printing secret values."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--staged',action='store_true');args=parser.parse_args()
command=['git','ls-files','--cached','-z'] if args.staged else ['git','ls-files','--cached','--others','--exclude-standard','-z']
raw=subprocess.check_output(command,cwd=ROOT)
paths=sorted(set(p.decode('utf-8') for p in raw.split(b'\0') if p))
patterns={
    'GitHub token':rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'OpenAI key':rb'sk-(?:proj-)?[A-Za-z0-9_-]{40,}',
    'AWS access key':rb'AKIA[0-9A-Z]{16}',
    'private key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'JWT credential':rb'eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}',
}
problems=[];total=0
for name in paths:
    source=ROOT/name
    if not source.is_file():continue
    body=subprocess.check_output(['git','show',':'+name],cwd=ROOT) if args.staged else source.read_bytes()
    size=len(body);total+=size
    if size>20*1024*1024:problems.append((name,'file larger than 20 MiB'))
    if source.suffix.lower() in {'.exe','.dll','.jar','.zip','.mp4','.pem','.key'}:problems.append((name,'excluded binary/private artifact'))
    if source.name.lower() in {'accounts.json','launcher_accounts.json','server.json','settings.json','.env'}:problems.append((name,'runtime/account file'))
    if source.suffix.lower() in {'.png','.ico','.woff2'}:continue
    for label,pattern in patterns.items():
        if re.search(pattern,body):problems.append((name,label))
    if source.suffix.lower()=='.json':
        try:data=json.loads(body.decode('utf-8-sig'))
        except (ValueError,UnicodeError):continue
        def sensitive(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if re.sub(r'[^a-z]','',key.lower()) in {'accesstoken','refreshtoken','idtoken','password','clientsecret','authorization','cookie','devicecode','sessiontoken','xbltoken','xststoken','minecrafttoken'} and isinstance(item,str) and item and item!='<REDACTED>':return True
                    if sensitive(item):return True
            elif isinstance(value,list):return any(sensitive(item) for item in value)
            return False
        if sensitive(data):problems.append((name,'nonempty credential field'))
manifest=ROOT/'docs/evidence/manifest.json'
if manifest.exists():
    data=json.loads(manifest.read_text(encoding='utf-8'))
    for name,entry in data['entries'].items():
        source=ROOT/'docs/evidence'/name
        body=subprocess.check_output(['git','show',':'+source.relative_to(ROOT).as_posix()],cwd=ROOT) if args.staged and source.exists() else source.read_bytes() if source.exists() else b''
        if not source.is_file() or hashlib.sha256(body).hexdigest()!=entry['published_sha256']:
            problems.append((str(source.relative_to(ROOT)),'evidence hash mismatch'))
if problems:
    for name,reason in problems:print(f'BLOCKED: {name}: {reason}')
    sys.exit(1)
print(f'Publication checks passed: {len(paths)} files, {total/1048576:.2f} MiB; evidence hashes match.')
