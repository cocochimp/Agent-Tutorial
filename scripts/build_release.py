"""干净发行包：只允许源码/样例/文档/模型，不收录密钥及运行状态。"""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='estate_agent_langgraph_demo'
ROOT_FILES=['app.py','launch.py','mcp_server.py','evaluate.py','README.md','代码导读.md','requirements.txt','requirements.in','project_config.json','eval_cases.json','deepseek_config.example.json','fallback_model_config.example.json','start_demo.cmd','start_demo.ps1','.gitignore']
FOLDERS=['estate_agent','web','docs','scripts','tests','extras','models']

def main():
    # 发布前同步两套源码镜像，避免新增注释后网页仍显示旧行号。
    from build_manual import main as build_manual
    from build_tutorial import main as build_tutorial
    build_manual()
    build_tutorial()
    out=ROOT/'dist';out.mkdir(exist_ok=True)
    files=[ROOT/f for f in ROOT_FILES]
    for folder in FOLDERS:
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file(): continue
            if any(x in path.parts for x in ('__pycache__','.pytest_cache','__MACOSX','.locks')): continue
            if path.name in ('.DS_Store','files_metadata.json') or path.name.startswith('._') or path.name.endswith('_v1_reference.txt'): continue
            files.append(path)
    files += [ROOT/'data'/'knowledge.json',ROOT/'data'/'relations.json',ROOT/'output'/'eval_results.json',ROOT/'output'/'pytest-results.xml',ROOT/'output'/'lora_adapter'/'training_result.json']
    manifest={}
    target=out/(NAME+'.zip')
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(set(files)):
            relative=path.relative_to(ROOT).as_posix();data=path.read_bytes()
            z.writestr(NAME+'/'+relative,data)
            manifest[relative]=hashlib.sha256(data).hexdigest()
        blank=(ROOT/'deepseek_config.example.json').read_bytes()
        assert not json.loads(blank.decode('utf-8-sig'))['api_key']
        z.writestr(NAME+'/deepseek_config.json',blank)
        manifest['deepseek_config.json']=hashlib.sha256(blank).hexdigest()
        z.writestr(NAME+'/MANIFEST.sha256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert not any('/state/' in n or '/.venv/' in n or n.endswith('.sqlite3') for n in z.namelist())
    sha=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(sha+'  '+target.name+'\n',encoding='ascii')
    print(json.dumps({'zip':str(target),'files':len(manifest),'size_mb':round(target.stat().st_size/1e6,1),'sha256':sha},indent=2))

if __name__=='__main__': main()
