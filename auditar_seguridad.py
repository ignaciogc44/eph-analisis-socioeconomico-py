"""Revisión local de archivos publicables; no imprime valores de credenciales."""
from pathlib import Path
import ast
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parent
EXCLUDED={'.venv','__pycache__','.git','personas','hogares','api','downloads','.ipynb_checkpoints'}
PATTERNS={
    'clave privada':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'token GitHub':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
    'clave AWS':r'\bAKIA[A-Z0-9]{16}\b',
    'token con formato JWT':r'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',
    'secreto literal':r'''(?im)^\s*(?:api_key|password|secret|access_token|INDEC_API_TOKEN)\s*=\s*["'][^"'\r\n]{8,}["']''',
    'ruta personal absoluta':r'[A-Za-z]:[\\/](?:Users|Archivos compartidos)[\\/]',
}

def run():
    findings=[];scanned=0
    for path in ROOT.rglob('*'):
        rel=path.relative_to(ROOT)
        if not path.is_file() or any(p in EXCLUDED for p in rel.parts): continue
        if path.suffix.lower() not in {'.py','.json','.md','.toml','.yaml','.yml','.txt','.cmd','.css'} and path.name!='.gitignore': continue
        scanned+=1
        text=path.read_text(encoding='utf-8-sig',errors='replace')
        for label,pattern in PATTERNS.items():
            if re.search(pattern,text): findings.append({'archivo':rel.as_posix(),'tipo':label})
        if path.suffix=='.py':
            tree=ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'eval','exec'}:
                    findings.append({'archivo':rel.as_posix(),'tipo':'ejecución dinámica','linea':node.lineno})
    # Verificación real de las exclusiones, sin inicializar ni modificar el proyecto Git.
    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run(['git','init','--quiet',folder],check=True)
        Path(folder,'.gitignore').write_bytes((ROOT/'.gitignore').read_bytes())
        protected=['.env','.env.production','.streamlit/secrets.toml','certificado.key','data/personas/base.txt','data/hogares/base.txt','data/api/ipc.json','.venv/config','cache.ipynb','tablero.pbix']
        result=subprocess.run(['git','-C',folder,'check-ignore','--stdin','-z'],input=('\0'.join(protected)+'\0').encode(),capture_output=True)
        assert result.returncode in (0,1), result.stderr.decode(errors='replace')
        missing=set(protected)-set(result.stdout.decode().split('\0'))
        assert not missing, sorted(missing)
    print(json.dumps({'archivos_revisados':scanned,'hallazgos':findings,'exclusiones_git_verificadas':len(protected)},ensure_ascii=False,indent=2))
    assert not findings,'Revisar hallazgos antes de publicar'

if __name__=='__main__': run()
