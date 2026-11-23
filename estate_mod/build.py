"""Stage/build outside OneDrive. Requires the pinned Gradle downloaded to local tools."""
from pathlib import Path
import os,shutil,subprocess,argparse
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--task',default='build');args=parser.parse_args()
local=Path(os.environ['LOCALAPPDATA']);stage=local/'PocketmateEstateBuild'
stage.mkdir(exist_ok=True)
for name in ['settings.gradle','build.gradle','gradle.properties']:
    shutil.copy2(root/name,stage/name)
for file in (stage/'src').rglob('*'):
    if file.is_file() and not (root/'src'/file.relative_to(stage/'src')).exists():file.unlink()
shutil.copytree(root/'src',stage/'src',dirs_exist_ok=True)
env=os.environ.copy();env['JAVA_HOME']=r'C:\Program Files\Java\jdk-21.0.12'
env['PATH']=env['JAVA_HOME']+r'\bin;'+env['PATH']
env['GRADLE_USER_HOME']=str(local/'PocketmateEstateTools/gradle-cache')
gradle=local/'PocketmateEstateTools/gradle-8.12.1/bin/gradle.bat'
subprocess.run([str(gradle),args.task,'--console=plain','--no-daemon'],cwd=stage,env=env,check=True)
dist=root/'dist';dist.mkdir(exist_ok=True)
for file in (stage/'build/libs').glob('*.jar'):shutil.copy2(file,dist/file.name)
if (stage/'build/test-results').exists():shutil.copytree(stage/'build/test-results',root/'verification/test-results',dirs_exist_ok=True)
