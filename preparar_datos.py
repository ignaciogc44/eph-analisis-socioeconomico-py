"""Importa la instantánea auditada sin modificar sus archivos de origen."""
from pathlib import Path
import argparse, hashlib, json, shutil
import pandas as pd
from metrics import ROOT

def prepare(source):
    target=ROOT/'data'; target.mkdir(exist_ok=True)
    manifest=[]
    for folder,out in [('Bases Personas','personas'),('Bases Hogares','hogares')]:
        (target/out).mkdir(exist_ok=True)
        for f in sorted((source/folder).glob('*.txt')):
            dest=target/out/f.name
            shutil.copy2(f,dest)
            manifest.append({'archivo':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'procedencia':'Microdatos EPH INDEC; bases oficiales de personas y hogares'})
    w=source/'EPH.xlsx'
    cities=pd.read_excel(w,sheet_name='Aglomerados',header=1,usecols='B:F')
    regions=pd.read_excel(w,sheet_name='Regiones',header=1,usecols='B:C')
    caes=pd.read_excel(w,sheet_name='Clasif',header=1,usecols='A:E').dropna(subset=['Clase'])
    codes={int(r.Clase):str(r.Seccion_desc).strip() for r in caes.itertuples()}
    for c in [10,19,20,22,24,26,27]: codes[c]='Industria Manufacturera'
    codes.update({1:'Agricultura, Ganadería, Caza, Silvicultura y Pesca',52:'Transporte y Almacenamiento',86:'Salud Humana y Servicios Sociales',88:'Salud Humana y Servicios Sociales',9999:'Actividad no especificada',9900:'Organismos Extraterritoriales'})
    ipc=pd.read_excel(source/'IPC.xlsx',header=1,usecols='A:B').dropna()
    ipc.columns=['Fecha','Indice'];ipc.Fecha=pd.to_datetime(ipc.Fecha)
    ipc=ipc[ipc.Fecha.between('2024-01-01','2025-12-31')].copy()
    ipc['Periodo']=ipc.Fecha.dt.year.astype(str)+' - '+ipc.Fecha.dt.quarter.astype(str)+'T'
    factors=(ipc.groupby('Periodo').Indice.mean()/ipc.Indice.max()).to_dict()
    ref={'cities':{int(r.Cod):str(r.Ciudad).strip() for r in cities.dropna(subset=['Cod']).itertuples()},'regions':{int(r.Cod):str(r.Region).strip() for r in regions.dropna(subset=['Cod']).itertuples()},'caes':codes,'deflators':factors,'ipc_mode':'Réplica del IPC.xlsx usado por Power BI (instantánea fija)','price_base':'diciembre de 2025, según las fechas de IPC.xlsx','ipc_reference_value':float(ipc.Indice.max()),'source_home':'https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos-1','api_docs':'https://api.indec.gob.ar/docs'}
    (target/'reference.json').write_text(json.dumps(ref,ensure_ascii=False,indent=2),encoding='utf-8')
    ipc.to_csv(target/'ipc_referencia.csv',index=False)
    (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    for name in ['recalculo_independiente.json','revision_pagina7_corregida.json']:
        f=source/'auditoria_indec'/name
        if f.exists():
            (target/'benchmarks').mkdir(exist_ok=True);shutil.copy2(f,target/'benchmarks'/name)
    if (target/'ipc_oficial.xls').exists():
        from actualizar_ipc import update
        update()
    print(f'Importados {len(manifest)} archivos; {len(codes)} códigos CAES; {len(factors)} trimestres.')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('source',type=Path);prepare(a.parse_args().source)
