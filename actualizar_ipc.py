"""Carga el IPC nacional directamente de la serie histórica oficial del INDEC."""
from pathlib import Path
import hashlib,io,json,urllib.request
import pandas as pd
from metrics import ROOT

URL='https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_01_26.xls'

def update():
    raw=urllib.request.urlopen(URL,timeout=60).read()
    sheet=pd.read_excel(io.BytesIO(raw),sheet_name=2,header=None,engine='xlrd')
    assert sheet.iloc[5,0].strip()=='Total nacional'
    assert sheet.iloc[9,0].strip()=='Nivel general'
    dates=pd.to_datetime(sheet.iloc[5,1:],errors='coerce')
    values=pd.to_numeric(sheet.iloc[9,1:],errors='coerce')
    d=pd.DataFrame({'Fecha':dates.to_numpy(),'Indice':values.to_numpy()}).dropna()
    d=d.loc[d.Fecha.between('2024-01-01','2025-12-01')].copy()
    assert len(d)==24 and not d.Fecha.duplicated().any()
    d['Periodo']=d.Fecha.dt.year.astype(str)+' - '+d.Fecha.dt.quarter.astype(str)+'T'
    base=float(d.loc[d.Fecha.eq('2025-12-01'),'Indice'].iloc[0])
    assert base>0 and d.groupby('Periodo').size().eq(3).all()
    refpath=ROOT/'data/reference.json'
    ref=json.loads(refpath.read_text(encoding='utf-8'))
    old=ROOT/'data/benchmarks/ipc_inicial.json'
    if not old.exists():
        old.write_text(json.dumps({k:ref.get(k) for k in ['deflators','price_base','ipc_reference_value']},indent=2),encoding='utf-8')
    ref.update(deflators=(d.groupby('Periodo').Indice.mean()/base).to_dict(),price_base='diciembre de 2025',ipc_reference_value=base,ipc_mode='IPC nacional oficial INDEC; promedio trimestral / diciembre de 2025',ipc_source=URL,ipc_source_sha256=hashlib.sha256(raw).hexdigest())
    d.to_csv(ROOT/'data/ipc_referencia.csv',index=False)
    refpath.write_text(json.dumps(ref,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'data/ipc_oficial.xls').write_bytes(raw)
    print('IPC nacional oficial actualizado:',len(d),'meses; diciembre 2025 =',base)

if __name__=='__main__': update()
