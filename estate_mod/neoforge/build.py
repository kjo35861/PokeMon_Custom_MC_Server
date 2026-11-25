"""Build the NeoForge distribution outside OneDrive. Does not launch Minecraft."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

here = Path(__file__).resolve().parent
local = Path(os.environ["LOCALAPPDATA"])
stage = local / "PocketmateNeoForgeBuild"
gradle = local / "PocketmateEstateTools/gradle-8.12.1/bin/gradle.bat"
env = os.environ.copy()
env.setdefault("JAVA_HOME", r"C:\Program Files\Java\jdk-21.0.12")
subprocess.run([sys.executable, str(here / "prepare.py")], check=True)
subprocess.run([str(gradle), "-p", str(stage), "build", "--no-daemon", "--console=plain"], check=True, env=env)
dist = here.parent / "dist"
dist.mkdir(exist_ok=True)
jar = stage / "build/libs/pocketmate-estates-neoforge-0.15.4.jar"
shutil.copy2(jar, dist / jar.name)
