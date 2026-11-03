"""Definiciones ponderadas del tablero EPH revisado. Sin dependencia de la interfaz."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
KEYS = ['CODUSU', 'NRO_HOGAR', 'ANO4', 'TRIMESTRE']
EDUCATION = {7:'Sin instrucción',1:'Primario incompleto',2:'Primario completo',3:'Secundario incompleto',4:'Secundario completo',5:'Superior/universitario incompleto',6:'Superior/universitario completo'}
OCCUPATION = {1:'Patrón',2:'Cuenta propia',3:'Obrero o empleado',4:'Familiar sin remuneración'}
INACTIVITY = {1:'Jubilado/pensionado',2:'Rentista',3:'Estudiante',4:'Tareas del hogar',5:'Menor de 6 años',6:'Personas con discapacidad',7:'Otros'}
DWELLING = {1:'Casa',2:'Departamento',3:'Pieza en inquilinato',4:'Pieza en pensión/hotel',5:'Local no destinado a vivienda',6:'Otro tipo de vivienda'}
TENURE = {1:'Propietario de vivienda y terreno',2:'Propietario de vivienda',3:'Inquilino',4:'Ocupante',5:'Ocupante',6:'Ocupante',7:'Ocupante',8:'En sucesión',9:'Otros'}
PCOLS = KEYS + ['COMPONENTE','PONDERA','PONDIIO','PONDII','PONDIH','ESTADO','CAT_OCUP','CAT_INAC','PP07H','P21','P47T','CH06','CH09','NIVEL_ED','CH04','AGLOMERADO','REGION','PP04B_COD']
HCOLS = KEYS + ['PONDERA','PONDIH','IPCF','DECCFR','AGLOMERADO','REGION','IV1','IV3','IV4','IV5','IV7','IV11','II7','II8']

def read_microdata(path, cols):
    d = pd.read_csv(path, sep=';', encoding='latin1', usecols=lambda c:c in cols, low_memory=False)
    missing = set(cols)-set(d.columns)
    if missing: raise ValueError(f'{path.name}: faltan columnas {sorted(missing)}')
    for c in d.columns:
        if c != 'CODUSU': d[c] = pd.to_numeric(d[c].astype(str).str.replace(',','.',regex=False), errors='coerce')
    return d

def load_data():
    ref = json.loads((ROOT/'data/reference.json').read_text(encoding='utf-8'))
    persons = list((ROOT/'data/personas').glob('*.txt'))
    households = list((ROOT/'data/hogares').glob('*.txt'))
    if not persons or not households: raise FileNotFoundError('Faltan bases EPH en data/personas o data/hogares. Descargá las bases con sync_sources.py eph, como indica el README.')
    p = pd.concat([read_microdata(f,PCOLS) for f in sorted(persons)],ignore_index=True)
    h = pd.concat([read_microdata(f,HCOLS) for f in sorted(households)],ignore_index=True)
    if p.duplicated(KEYS+['COMPONENTE']).any() or h.duplicated(KEYS).any(): raise ValueError('Claves duplicadas: revisar bases antes de calcular.')
    caes = {int(k):v for k,v in ref['caes'].items()}
    for d in [p,h]:
        d['Periodo'] = d.ANO4.astype(int).astype(str)+' - '+d.TRIMESTRE.astype(int).astype(str)+'T'
        d['Región'] = d.REGION.map({int(k):v for k,v in ref['regions'].items()}).fillna('Sin región')
        d['Aglomerado'] = d.AGLOMERADO.map({int(k):v for k,v in ref['cities'].items()}).fillna('Sin aglomerado')
    p['Sexo'] = p.CH04.map({1:'Varón',2:'Mujer'}).fillna('Sin información')
    p['Sector'] = p.PP04B_COD.map(caes).fillna('Sin clasificación')
    p['Nivel educativo'] = p.NIVEL_ED.map(EDUCATION).fillna('Sin información')
    p['Situación'] = p.ESTADO.map({0:'Sin información',1:'Ocupados',2:'Desocupados',3:'Inactivos',4:'Inactivos'}).fillna('Sin información')
    p['Estado detallado'] = p.ESTADO.map({0:'Entrevista no realizada',1:'Ocupados',2:'Desocupados',3:'Inactivos de 10 años o más',4:'Menores de 10 años'})
    p['Categoría ocupacional'] = p.CAT_OCUP.map(OCCUPATION)
    p['Categoría de inactividad'] = p.CAT_INAC.map(INACTIVITY)
    h['Tipo de vivienda'] = h.IV1.map(DWELLING).fillna('No especificado')
    h['Tenencia'] = h.II7.map(TENURE).fillna('No especificado')
    # Mismas reglas de materiales que el modelo auditado.
    roof_bad = h.IV4.isin([6,7]) | (h.IV4.isin([4,5]) & h.IV5.eq(2))
    roof_partial = h.IV4.isin([1,2,3,9]) & h.IV5.eq(2)
    h['Materiales insuficientes'] = h.IV3.isin([2,3,4]) | roof_bad | roof_partial
    housing_cols = ['IV7','IV11','II8','Materiales insuficientes','Tipo de vivienda','Tenencia']
    p = p.merge(h[KEYS+housing_cols],on=KEYS,how='left',validate='many_to_one',indicator=True)
    if p['_merge'].ne('both').any(): raise ValueError('Personas sin hogar asociado.')
    p = p.drop(columns='_merge')
    return p,h,ref

def select(d, period=None, regions=(), cities=(), sexes=()):
    mask = pd.Series(True,index=d.index)
    if period: mask &= d.Periodo.eq(period)
    if regions: mask &= d['Región'].isin(regions)
    if cities: mask &= d.Aglomerado.isin(cities)
    if sexes and 'Sexo' in d: mask &= d.Sexo.isin(sexes)
    return d.loc[mask]

def ratio(n,d):
    return float(n/d) if d else float('nan')

def share(d,mask,w='PONDERA'):
    return 100*ratio(d.loc[mask,w].sum(),d[w].sum())

def mean(d,col,w):
    valid = d[col].notna() & d[w].notna() & d[w].gt(0)
    a=d.loc[valid]
    return ratio((a[col]*a[w]).sum(),a[w].sum())

def distribution(d,group,w='PONDERA',within=None):
    cols = ([within] if within else [])+[group]
    g=d.groupby(cols,observed=True,dropna=False)[w].sum().rename('Personas ponderadas').reset_index()
    den=g.groupby(within)['Personas ponderadas'].transform('sum') if within else g['Personas ponderadas'].sum()
    g['Porcentaje']=100*g['Personas ponderadas']/den
    return g

def rates(d):
    pea=d.ESTADO.isin([1,2]); employed=d.ESTADO.eq(1)
    salary=d.loc[employed & d.CAT_OCUP.eq(3) & d.PP07H.isin([1,2])]
    return {'Actividad':share(d,pea),'Empleo':share(d,employed),'Desocupación':share(d.loc[pea],d.loc[pea,'ESTADO'].eq(2)), 'Sin descuento jubilatorio':share(salary,salary.PP07H.eq(2))}

def eligible_salary(d): return d.loc[d.ESTADO.eq(1)&d.CAT_OCUP.eq(3)&d.P21.gt(0)]
def eligible_individual(d): return d.loc[d.ESTADO.isin([1,2])&d.P47T.gt(0)]

def grouped_income(d,groups,col,w,ref,real=True):
    rows=[]
    for keys,a in d.groupby(groups,observed=True,dropna=False):
        keys=keys if isinstance(keys,tuple) else (keys,)
        factor=ref['deflators'].get(a.Periodo.iloc[0]) if real else 1
        value=mean(a,col,w)
        rows.append(dict(zip(groups,keys))|{'Ingreso':value/factor if factor else np.nan,'Casos muestrales':len(a),'Ponderación':float(a[w].sum())})
    return pd.DataFrame(rows,columns=groups+['Ingreso','Casos muestrales','Ponderación'])

def housing_summary(d):
    return {'Sin agua de red':share(d,d.IV7.ne(1)),'Sin gas de red':share(d,d.II8.ne(1)),'Sin cloacas':share(d,d.IV11.ne(1)),'Materiales insuficientes':share(d,d['Materiales insuficientes'].fillna(False))}
