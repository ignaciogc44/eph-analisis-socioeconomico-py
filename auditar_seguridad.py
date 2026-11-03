"""Revisa archivos publicables, el índice y el historial Git sin imprimir secretos."""
from pathlib import Path
import ast
import json
import os
import re
import subprocess
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent
EXCLUDED={'.venv','__pycache__','.git','personas','hogares','api','downloads','.ipynb_checkpoints','tmp'}
TEXT={'.py','.json','.md','.toml','.yaml','.yml','.txt','.cmd','.css'}
PATTERNS={
    'clave privada':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'token GitHub':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
    'clave AWS':r'\bAKIA[A-Z0-9]{16}\b',
    'token JWT':r'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',
    'secreto literal':r'''(?im)^\s*(?:api_key|password|secret|access_token|INDEC_API_TOKEN)\s*=\s*["'][^"'\r\n]{8,}["']''',
    'ruta personal absoluta':r'[A-Za-z]:[\\/](?:Users|Archivos compartidos)[\\/]',
}

def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])

def forbidden(name):
    path=Path(name)
    return any(p in {'.venv','personas','hogares','api','downloads','tmp'} for p in path.parts) or (path.name.startswith('.env') and path.name!='.env.example') or path.name=='secrets.toml' or path.suffix in {'.pem','.key','.pfx','.p12','.pbix'}

def run():
    findings=[];scanned=0;history_count=0
    def scan(name,raw,origin):
        if forbidden(name): findings.append({'archivo':name,'tipo':'archivo privado','origen':origin})
        path=Path(name)
        if path.suffix.lower() not in TEXT and path.name not in {'.gitignore','.gitattributes'}: return
        text=raw.decode('utf-8-sig',errors='replace')
        for label,pattern in PATTERNS.items():
            if re.search(pattern,text): findings.append({'archivo':name,'tipo':label,'origen':origin})
        if path.suffix=='.py':
            for node in ast.walk(ast.parse(text)):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'eval','exec'}:
                    findings.append({'archivo':name,'tipo':'ejecución dinámica','linea':node.lineno,'origen':origin})
    if (ROOT/'.git').exists():
        tracked=set(git('ls-files','-z').decode().split('\0'))-{''}
        others=set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
        for name in sorted(tracked|others):
            if name in tracked: scan(name,git('show',':'+name),'índice')
            path=ROOT/name
            if path.is_file():scan(name,path.read_bytes(),'trabajo')
            scanned+=1
        for item in git('rev-list','--objects','--all').decode().splitlines():
            if ' ' not in item:continue
            oid,name=item.split(' ',1)
            if git('cat-file','-t',oid).strip()!=b'blob':continue
            scan(name,git('cat-file','blob',oid),'historial');history_count+=1
        authors=git('log','--all','--format=%ae').decode().splitlines()
        if any(not a.endswith('@users.noreply.github.com') for a in authors):
            findings.append({'tipo':'correo de autor sin noreply','origen':'historial'})
        remotes=git('remote','get-url','origin').decode().strip()
        url=urlsplit(remotes)
        if url.password or url.username: findings.append({'tipo':'credencial en URL remota'})
    else:
        for folder,dirs,files in os.walk(ROOT):
            dirs[:]=[d for d in dirs if d not in EXCLUDED]
            for name in files:
                path=Path(folder)/name;scan(path.relative_to(ROOT).as_posix(),path.read_bytes(),'trabajo');scanned+=1
    protected=['.env','.env.production','.streamlit/secrets.toml','certificado.key','data/personas/base.txt','data/hogares/base.txt','data/api/ipc.json','.venv/config','cache.ipynb','tablero.pbix','tmp/export.png','.vscode/settings.json','preparar_datos.py','data/ipc_oficial.xls','auditoria_dependencias.json']
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run(['git','init','--quiet',folder],check=True)
        Path(folder,'.gitignore').write_bytes((ROOT/'.gitignore').read_bytes())
        result=subprocess.run(['git','-C',folder,'check-ignore','--stdin','-z'],input=('\0'.join(protected)+'\0').encode(),capture_output=True,check=True)
        missing=set(protected)-set(result.stdout.decode().split('\0'))
        if missing:raise RuntimeError('Hay exclusiones Git sin cobertura.')
    print(json.dumps({'archivos_publicables':scanned,'blobs_historial':history_count,'hallazgos':findings,'exclusiones_git_verificadas':len(protected)},ensure_ascii=False,indent=2))
    if findings:raise RuntimeError('Revisar los hallazgos antes de publicar.')

if __name__=='__main__':run()
