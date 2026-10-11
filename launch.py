"""安装环境并从同源HTTP页面运行，避免file://导致Failed to fetch。"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    if sys.version_info<(3,11):
        raise SystemExit('Python 3.11+ required. Python 3.13 recommended.')
    python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists(): subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv')],check=True)
    version=subprocess.check_output([str(python),'-c','import sys; print(".".join(map(str,sys.version_info[:3])))'],text=True).strip()
    print(f'Project Python: {version}\nInterpreter: {python}',flush=True)
    if tuple(map(int,version.split('.')[:2])) < (3,11):
        raise SystemExit('The existing .venv requires Python 3.11+. Please recreate it with a supported Python.')
    req=ROOT/'requirements.txt'; stamp=ROOT/'.venv'/'.requirements.sha256'
    digest=hashlib.sha256(req.read_bytes()).hexdigest()
    if not stamp.exists() or stamp.read_text()!=digest:
        try:
            subprocess.run([str(python),'-m','pip','install','-r',str(req)],check=True)
            subprocess.run([str(python),'-m','pip','check'],check=True)
        except subprocess.CalledProcessError:
            print('\nDependency installation failed. See the pip error above. Fix it and run start_demo.cmd again.',flush=True)
            return 1
        stamp.write_text(digest)
    config=ROOT/'deepseek_config.json'
    if not config.exists(): config.write_bytes((ROOT/'deepseek_config.example.json').read_bytes())
    print('\nOpen http://127.0.0.1:8765  |  Stop: Ctrl+C\n',flush=True)
    return subprocess.call([str(python),'-X','utf8',str(ROOT/'app.py'),*sys.argv[1:]])

if __name__=='__main__': raise SystemExit(main())
