"""Build against locally installed MC and Fabric libraries; no account files are accessed."""
from pathlib import Path
import os
import subprocess
import zipfile

root = Path(__file__).resolve().parent
prism = Path(os.environ['APPDATA'])/'PrismLauncher'
libraries = prism/'libraries'
java = Path(r'C:\Program Files\Java\jdk-21.0.12\bin\javac.exe')
client = Path(os.environ['LOCALAPPDATA'])/'SnowfrostLauncher/game/versions/1.21.1/1.21.1.jar'
dependencies = [client, next(libraries.rglob('sponge-mixin-*.jar')),
                next(libraries.rglob('lwjgl-opengl-3.3.3.jar')), next(libraries.rglob('lwjgl-3.3.3.jar'))]
classes = root/'build/classes'
classes.mkdir(parents=True, exist_ok=True)
subprocess.run([str(java), '--release', '21', '-proc:none', '-cp', os.pathsep.join(map(str,dependencies)),
                '-d', str(classes), *map(str,(root/'src').rglob('*.java'))], check=True)
output = root/'dist/pocketmate-webgui-alpha-0.1.0.jar'
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as jar:
    for path in classes.rglob('*.class'): jar.write(path,path.relative_to(classes).as_posix())
    for name in ['fabric.mod.json','pocketmate-webgui-alpha.mixins.json']:jar.write(root/name,name)
print(str(output))
