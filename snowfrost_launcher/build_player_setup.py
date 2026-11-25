"""Build a standalone Windows setup executable from a Pocketmate player ZIP."""
import argparse
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("zip", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent
with zipfile.ZipFile(args.zip) as archive:
    required = {"PocketmateLauncher.exe", "launcher-config.json", "client-pack.json"}
    if not required <= set(archive.namelist()) or archive.testzip() is not None:
        raise SystemExit("Invalid Pocketmate player ZIP")
csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
with tempfile.TemporaryDirectory(prefix="PocketmateSetupBuild-") as temp:
    stub = Path(temp) / "stub.exe"
    refs = ["System.Windows.Forms", "System.Drawing", "Microsoft.CSharp", "System.IO.Compression", "System.IO.Compression.FileSystem"]
    subprocess.run([str(csc), "/nologo", "/target:winexe", "/platform:x64", "/codepage:65001",
        *("/r:" + ref + ".dll" for ref in refs), "/win32icon:" + str(root / "assets/launcher.ico"),
        "/out:" + str(stub), str(root / "PlayerSetup.cs")], check=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pending = args.output.with_suffix(".pending")
    with pending.open("wb") as out, args.zip.open("rb") as payload:
        out.write(stub.read_bytes())
        shutil.copyfileobj(payload, out, 1024 * 1024)
        out.write(struct.pack("<q8s", payload.tell(), b"PMSETUP1"))
    os.replace(pending, args.output)
subprocess.run([str(args.output.resolve()), "--verify"], check=True, timeout=60)
print(args.output)
