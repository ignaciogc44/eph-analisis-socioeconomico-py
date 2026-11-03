"""Descargas explícitas desde INDEC. No sustituye automáticamente el IPC auditado."""
import argparse, hashlib, io, json, os, re, urllib.request, urllib.parse, zipfile
from datetime import datetime, timezone
from pathlib import Path
from metrics import ROOT

def fetch_eph(year,quarter):
    if not 2003<=year<=2100 or quarter not in range(1,5): raise ValueError('Período inválido')
    url=f'https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_usu_{quarter}_Trim_{year}_txt.zip'
    limit=64*1024*1024
    with urllib.request.urlopen(url,timeout=90) as response:
        raw=response.read(limit+1)
    if len(raw)>limit: raise ValueError('El ZIP supera el límite de descarga.')
    entries=[]
    expected=re.compile(rf'^usu_(individual|hogar)_T{quarter}{year%100:02d}\.txt$',re.I)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for member in z.infolist():
            name=Path(member.filename.replace('\\','/')).name
            if not name.lower().endswith('.txt'): continue
            unit='personas' if name.lower().startswith('usu_individual') else 'hogares' if name.lower().startswith('usu_hogar') else None
            if unit:
                if not expected.fullmatch(name): raise ValueError('Nombre o período inesperado en el ZIP.')
                if member.file_size>64*1024*1024: raise ValueError('Base EPH demasiado grande.')
                if any(e[0]==unit for e in entries): raise ValueError('Base EPH duplicada en el ZIP.')
                entries.append((unit,name,z.read(member)))
    if {e[0] for e in entries}!={'personas','hogares'}: raise ValueError('El ZIP no contiene ambas bases EPH esperadas.')
    for unit,name,content in entries:
        out=ROOT/'data'/unit/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(content)
    record={'url':url,'sha256_zip':hashlib.sha256(raw).hexdigest(),'fecha_descarga':datetime.now(timezone.utc).isoformat(),'archivos':[e[1] for e in entries]}
    out=ROOT/'data/downloads';out.mkdir(exist_ok=True)
    (out/f'eph_{year}_{quarter}.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(f'Descargadas ambas bases oficiales: {year} - {quarter}T. Reiniciá la app o limpiá su caché para cargarlas.')

def fetch_api(dataset,filters):
    if dataset not in {'ipc_nacional','mercado_trabajo_eph'}: raise ValueError('Dataset no permitido.')
    token=os.environ.get('INDEC_API_TOKEN')
    if not token: raise ValueError('Definí INDEC_API_TOKEN en el entorno; obtenelo en https://api.indec.gob.ar/. No lo guardes en el código.')
    params=dict(item.split('=',1) for item in filters)
    # Orden completo recomendado por la documentación para paginar sin perder filas.
    order='clasificador,nivel,codigo,descripcion,periodo,anio,mes,indicador,tipo_de_indicador,tipo_de_indicador_descripcion,region,unidad_de_medida' if dataset=='ipc_nacional' else 'anio,trimestre,periodo'
    params.update(limit=1000,offset=0,order=order)
    rows=[]
    while True:
        req=urllib.request.Request('https://api.indec.gob.ar/v1/'+dataset+'?'+urllib.parse.urlencode(params),headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as response: batch=json.load(response)
        if not isinstance(batch,list): raise ValueError('Respuesta API inesperada; no se reemplazaron los datos activos.')
        rows.extend(batch)
        if len(batch)<1000: break
        params['offset']+=len(batch)
    out=ROOT/'data/api';out.mkdir(parents=True,exist_ok=True)
    (out/(dataset+'.json')).write_text(json.dumps({'dataset':dataset,'filters':filters,'downloaded_at':datetime.now(timezone.utc).isoformat(),'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(rows)} filas descargadas. Guardadas en data/api; no cambian el IPC activo sin conciliación.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    eph=sub.add_parser('eph');eph.add_argument('--year',type=int,required=True);eph.add_argument('--quarter',type=int,required=True)
    api=sub.add_parser('api');api.add_argument('dataset',choices=['ipc_nacional','mercado_trabajo_eph']);api.add_argument('--filter',action='append',default=[],help='Ejemplo: anio=eq.2025 (puede repetirse)')
    args=parser.parse_args()
    try:
        if args.command=='eph': fetch_eph(args.year,args.quarter)
        else: fetch_api(args.dataset,args.filter)
    except Exception as e: parser.exit(1,f'No se completó la descarga: {e}\n')
