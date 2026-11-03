"""Recalcula tablas desde TXT oficiales sin usar los helpers de metrics."""
from pathlib import Path
import hashlib
import json
import math
import pandas as pd
import charts
import metrics as m

ROOT = Path(__file__).resolve().parent
KEYS = ['CODUSU','NRO_HOGAR','ANO4','TRIMESTRE']
CHECKS = 0

def near(a,b):
    global CHECKS
    assert (pd.isna(a) and pd.isna(b)) or math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-6),(a,b)
    CHECKS += 1

def raw(unit):
    columns = set(KEYS+['COMPONENTE','CH03','PONDERA','PONDIIO','PONDII','PONDIH','ESTADO','CAT_OCUP','CAT_INAC','PP07H','P21','P47T','CH06','CH09','NIVEL_ED','CH04','AGLOMERADO','REGION','PP04B_COD','IPCF','DECCFR','IV1','IV3','IV4','IV5','IV7','IV11','II7','II8'])
    frames=[]
    for path in sorted((ROOT/'data'/unit).glob('*.txt')):
        a=pd.read_csv(path,sep=';',encoding='latin1',usecols=lambda c:c in columns,decimal=',',low_memory=False)
        for c in a:
            if c!='CODUSU': a[c]=pd.to_numeric(a[c],errors='raise')
        frames.append(a)
    return pd.concat(frames,ignore_index=True)

def pct(d,mask):
    return 100*d.loc[mask,'PONDERA'].sum()/d.PONDERA.sum()

def dist(actual,d,labels,group,within=None,count='Personas ponderadas'):
    labels=labels.reindex(d.index)
    valid=labels.notna()
    d=d.loc[valid].copy();d['_label']=labels.loc[valid]
    keys=([within] if within else [])+['_label']
    expected=d.groupby(keys,dropna=False).PONDERA.sum()
    assert len(actual)==len(expected),(group,len(actual),len(expected))
    for _,r in actual.iterrows():
        k=(r[within],r[group]) if within else r[group]
        n=expected.loc[k]
        denominator=d.loc[d[within].eq(r[within]),'PONDERA'].sum() if within else d.PONDERA.sum()
        near(r[count],n);near(r.Porcentaje,100*n/denominator)

def income(actual,d,groups,col,weight,factors):
    assert len(actual)==len(d.groupby(groups,dropna=False)),groups
    for _,r in actual.iterrows():
        a=d
        for group in groups: a=a.loc[a[group].eq(r[group])]
        period=f"{int(a.ANO4.iloc[0])} - {int(a.TRIMESTRE.iloc[0])}T"
        a_valid=a.loc[a[weight].gt(0)&a[col].notna()]
        near(r.Ingreso,(a_valid[col]*a_valid[weight]).sum()/a_valid[weight].sum()/factors[period])
        near(r['Casos muestrales'],len(a));near(r['Ponderación'],a[weight].sum())

def run():
    rp,rh=raw('personas'),raw('hogares')
    for item in json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8-sig')):
        near(int(hashlib.sha256((ROOT/item['archivo']).read_bytes()).hexdigest()==item['sha256']),1)
    assert not rp.duplicated(KEYS+['COMPONENTE']).any()
    assert not rh.duplicated(KEYS).any()
    rp=rp.merge(rh[KEYS+['IV1','IV3','IV4','IV5','IV7','IV11','II7','II8']],on=KEYS,validate='many_to_one')
    ref=json.loads((ROOT/'data/reference.json').read_text(encoding='utf-8'))
    for d in [rp,rh]:
        d['Periodo']=d.ANO4.astype(int).astype(str)+' - '+d.TRIMESTRE.astype(int).astype(str)+'T'
        d['Región']=d.REGION.map({int(k):v for k,v in ref['regions'].items()})
        d['Aglomerado']=d.AGLOMERADO.map({int(k):v for k,v in ref['cities'].items()})
    rp['Sexo']=rp.CH04.map({1:'Varón',2:'Mujer'})
    rp['Sector']=rp.PP04B_COD.map({int(k):v for k,v in ref['caes'].items()}).fillna('Sin clasificación')
    ipc=pd.read_csv(ROOT/'data/ipc_referencia.csv',parse_dates=['Fecha'])
    base=ipc.loc[ipc.Fecha.eq('2025-12-01'),'Indice'].item()
    factors={k:g.Indice.mean()/base for k,g in ipc.groupby('Periodo')}
    p,h,_=m.load_data()
    # Evita construir figuras: esta prueba inspecciona las tablas que alimentan ambas interfaces.
    charts.figure=lambda *args,**kwargs: None
    tenure={1:'Propietario de vivienda y terreno',2:'Propietario de vivienda',3:'Inquilino',4:'Ocupante',5:'Ocupante',6:'Ocupante',7:'Ocupante',8:'En sucesión',9:'Otros'}
    occupation={1:'Patrón',2:'Cuenta propia',3:'Obrero o empleado',4:'Familiar sin remuneración'}
    inactivity={1:'Jubilado/pensionado',2:'Rentista',3:'Estudiante',4:'Tareas del hogar',5:'Menor de 6 años',6:'Personas con discapacidad',7:'Otros'}
    education={7:'Sin instrucción',1:'Primario incompleto',2:'Primario completo',3:'Secundario incompleto',4:'Secundario completo',5:'Superior/universitario incompleto',6:'Superior/universitario completo'}
    dwelling={1:'Casa',2:'Departamento',3:'Pieza en inquilinato',4:'Pieza en pensión/hotel',5:'Local no destinado a vivienda',6:'Otro tipo de vivienda'}
    tables=0
    for period in sorted(p.Periodo.unique()):
        a=rp.loc[rp.Periodo.eq(period)];b=rh.loc[rh.Periodo.eq(period)]
        pp=p.loc[p.Periodo.eq(period)];hh=h.loc[h.Periodo.eq(period)]
        specs={s.identity:s.rows for v in charts.VIEWS for s in charts.build(v,pp,hh,p,ref,period,sectors=sorted(rp.loc[rp.ESTADO.eq(1)&rp.CAT_OCUP.eq(3)&rp.P21.gt(0),'Sector'].unique()))}
        for identity,group,codes,d in [('dwelling','Tipo de vivienda',dwelling,a),('tenure','Tenencia',tenure,a),('occupation','Categoría ocupacional',occupation,a.loc[a.ESTADO.eq(1)]),('inactivity','Categoría de inactividad',inactivity,a.loc[a.ESTADO.eq(3)]),('education','Nivel educativo',education,a.loc[a.CH06.ge(18)])]:
            col={'dwelling':'IV1','tenure':'II7','occupation':'CAT_OCUP','inactivity':'CAT_INAC','education':'NIVEL_ED'}[identity]
            labels=d[col].map(codes)
            if identity in ['dwelling','tenure','education']: labels=labels.fillna('No especificado' if identity!='education' else 'Sin información')
            dist(specs[identity],d,labels,group);tables+=1
        for s in charts.build('Vivienda y servicios',pp,hh,p,ref,period,unit='Hogares')[:2]:
            col='IV1' if s.identity=='dwelling' else 'II7';group='Tipo de vivienda' if col=='IV1' else 'Tenencia'
            dist(s.rows,b,b[col].map(dwelling if col=='IV1' else tenure).fillna('No especificado'),group,count='Hogares ponderados');tables+=1
        dist(specs['sectors'],a.loc[a.ESTADO.eq(1)],a.Sector,'Sector');tables+=1
        d=a.copy();d['Sexo']=d.CH04.map({1:'Varón',2:'Mujer'})
        d=pd.concat([d,d.assign(Sexo='Total')],ignore_index=True)
        dist(specs['status_sex'],d,d.ESTADO.map({0:'Sin información',1:'Ocupados',2:'Desocupados',3:'Inactivos',4:'Inactivos'}),'Situación',within='Sexo');tables+=1
        dist(specs['population'],a,a.ESTADO.map({0:'Entrevista no realizada',1:'Ocupados',2:'Desocupados',3:'Inactivos de 10 años o más',4:'Menores de 10 años'}),'Estado detallado');tables+=1
        ed=a.loc[a.CH06.ge(18)]
        dist(specs['secondary'],ed,ed.NIVEL_ED.isin([4,5,6]).map({True:'Finalizó secundaria',False:'No finalizó secundaria'}),'Finalización');tables+=1
        for unit,raw_d in [('Personas',a),('Hogares',b)]:
            for territory in ['Región','Aglomerado']:
                rows=charts.build('Vivienda y servicios',pp,hh,p,ref,period,unit,territory)[-1].rows
                for _,r in rows.iterrows():
                    d=raw_d.loc[raw_d[territory].eq(r[territory])]
                    for label,col in [('Sin agua de red','IV7'),('Sin gas de red','II8'),('Sin cloacas','IV11')]: near(r[label],pct(d,d[col].ne(1)))
                    bad=d.IV3.isin([2,3,4])|d.IV4.isin([6,7])|(d.IV4.isin([4,5])&d.IV5.eq(2))|(d.IV4.isin([1,2,3,9])&d.IV5.eq(2))
                    near(r['Materiales insuficientes'],pct(d,bad))
                    literate=a.loc[a[territory].eq(r[territory])&a.CH06.ge(10)]
                    near(r['Analfabetismo · 10+'],pct(literate,literate.CH09.eq(2)))
                tables+=1
        d=b.loc[b.DECCFR.between(1,10)].rename(columns={'DECCFR':'Decil'})
        income(specs['deciles'],d,['Decil'],'IPCF','PONDIH',factors);tables+=1
        d=a.loc[a.ESTADO.isin([1,2])&a.P47T.gt(0)]
        d=pd.concat([d,d.assign(Sexo='Total')],ignore_index=True)
        income(specs['income_education'],d,['NIVEL_ED','Sexo'],'P47T','PONDII',factors);tables+=1
        if period=='2025 - 4T':
            print('OCUPACION 4T2025');print(specs['occupation'].to_string(index=False))
            print('TENENCIA CORREGIDA 4T2025');print(specs['tenure'].to_string(index=False))
    salary=rp.loc[rp.ESTADO.eq(1)&rp.CAT_OCUP.eq(3)&rp.P21.gt(0)]
    # El catálogo conserva las celdas vacías: solo se comparan grupos observados.
    rows=specs['income_history'].dropna(subset=['Casos muestrales'])
    income(rows,salary,['Periodo','Sector'],'P21','PONDIIO',factors);tables+=1
    for _,r in specs['labor_history'].iterrows():
        d=rp.loc[rp.Periodo.eq(r.Periodo)]
        if r.Indicador=='Actividad': expected=pct(d,d.ESTADO.isin([1,2]))
        elif r.Indicador=='Empleo': expected=pct(d,d.ESTADO.eq(1))
        elif r.Indicador=='Desocupación':
            d=d.loc[d.ESTADO.isin([1,2])];expected=pct(d,d.ESTADO.eq(2))
        else:
            d=d.loc[d.ESTADO.eq(1)&d.CAT_OCUP.eq(3)&d.PP07H.isin([1,2])];expected=pct(d,d.PP07H.eq(2))
        near(r.Porcentaje,expected)
    tables+=1
    from formatting import public_table,export_table
    for region in [None,'Cuyo','Pampeana']:
        base=rp.loc[rp.Periodo.eq('2025 - 4T')]
        selected=p.loc[p.Periodo.eq('2025 - 4T')]
        if region:
            base=base.loc[base['Región'].eq(region)]
            selected=selected.loc[selected['Región'].eq(region)]
        for sex in ['Mujer','Varón']:
            filtered=selected.loc[selected.Sexo.eq(sex)]
            composition=charts.build('Composición del mercado laboral',filtered,h,p,ref,'2025 - 4T',population=selected)[0]
            raw_sex=base.loc[base.Sexo.eq(sex)]
            raw_comparison=pd.concat([raw_sex,base.assign(Sexo='Total')],ignore_index=True)
            dist(composition.rows,raw_comparison,raw_comparison.ESTADO.map({0:'Sin información',1:'Ocupados',2:'Desocupados',3:'Inactivos',4:'Inactivos'}),'Situación',within='Sexo')
            result=charts.build('Ingresos y distribución',filtered,h.loc[h.Periodo.eq('2025 - 4T')],p,ref,'2025 - 4T',population=selected)[1]
            eligible=raw_comparison.loc[raw_comparison.ESTADO.isin([1,2])&raw_comparison.P47T.gt(0)]
            income(result.rows,eligible,['NIVEL_ED','Sexo'],'P47T','PONDII',factors)
            for spec in [composition,result]:
                visible=public_table(spec.rows)
                assert 'Total' in visible and sex in visible
                assert not {'Casos muestrales','Ponderación','NIVEL_ED'}.intersection(visible)
                assert len(export_table(spec.rows).columns)==3
    print(f'OK: {CHECKS} comprobaciones numéricas / integridad; {tables} tablas, 8 trimestres, ambas unidades y territorios. Clasificación CAES reutiliza el catálogo previamente auditado; no es una validación independiente de cada código CAES.')

if __name__=='__main__': run()
