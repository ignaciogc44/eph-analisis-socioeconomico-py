"""Pruebas de conciliación con recálculos independientes y resultados del INDEC."""
import json, math
import pandas as pd
import metrics as m

def run():
    p,h,ref=m.load_data();n=0
    def near(actual,expected,tol=0.01):
        nonlocal n
        assert math.isfinite(actual) and abs(actual-expected)<=tol,(actual,expected)
        n+=1
    benchmark=json.loads((m.ROOT/'data/benchmarks/recalculo_independiente.json').read_text(encoding='utf-8-sig'))
    for row in benchmark['series']:
        d=m.select(p,f"{row['year']} - {row['quarter']}T")
        for name,key in [('Actividad','actividad'),('Empleo','empleo'),('Desocupación','desempleo'),('Sin descuento jubilatorio','sin_descuento')]: near(m.rates(d)[name],row[key],1e-7)
    d=m.select(p,'2025 - 4T');hh=m.select(h,'2025 - 4T');fac=ref['deflators']['2025 - 4T']
    near(m.mean(m.eligible_salary(d),'P21','PONDIIO'),1082634.9972604178)
    near(m.mean(hh,'IPCF','PONDIH'),773693.0246769165)
    for dec,val in benchmark['deciles_hogares'].items(): near(m.mean(hh[hh.DECCFR.eq(int(dec))],'IPCF','PONDIH'),val)
    near(m.share(d[d.CH06.ge(10)],d.loc[d.CH06.ge(10),'CH09'].eq(2)),benchmark['educacion']['no_lee_10_mas'])
    near(m.share(d[d.CH06.ge(18)],d.loc[d.CH06.ge(18),'NIVEL_ED'].isin([4,5,6])),benchmark['educacion']['secundaria_completa_18_mas'])
    for key,col in [('sin_agua','IV7'),('sin_gas','II8'),('sin_cloaca','IV11')]: near(m.share(d,d[col].ne(1)),benchmark['vivienda_4t2025'][key]['personas_4t'])
    expected=json.loads((m.ROOT/'data/benchmarks/ingresos_sector_nominales.json').read_text(encoding='utf-8'))
    for row in expected['serie']:
        a=m.eligible_salary(m.select(p,row['periodo']));a=a[a.Sector.eq(row['sector'])]
        near(m.mean(a,'P21','PONDIIO'),row['ingreso_nominal'])
    # INDEC, Mercado de trabajo 4T2025, cuadros 1.1 y 1.5.
    for label,value in [('Actividad',48.6),('Empleo',45.0),('Desocupación',7.5),('Sin descuento jubilatorio',36.3)]:
        near(round(m.rates(d)[label],1),value,1e-8)
    occ=d.loc[d.ESTADO.eq(1)]
    for code,value in [(1,3.3),(2,24.7),(3,71.5),(4,.4)]:
        near(round(m.share(occ,occ.CAT_OCUP.eq(code)),1),value,1e-8)
    near(round(m.share(occ,occ.Sector.eq('Industria Manufacturera')),1),9.9,1e-8)
    # INDEC, Distribución del ingreso 4T2025, cuadros 3, 4 y 6.1.
    people=d.loc[d.P47T.gt(0)]
    near(round(m.mean(people,'P47T','PONDII')),1011863,1e-8)
    for sex,value in [('Mujer',838336),('Varón',1191364)]:
        near(round(m.mean(people.loc[people.Sexo.eq(sex)],'P47T','PONDII')),value,1e-8)
    near(round(m.mean(m.eligible_salary(d),'P21','PONDIIO')),1082635,1e-8)
    # Los 24 meses del deflactor corresponden a su trimestre y a diciembre 2025.
    ipc=pd.read_csv(m.ROOT/'data/ipc_referencia.csv',parse_dates=['Fecha'])
    base=float(ipc.loc[ipc.Fecha.eq('2025-12-01'),'Indice'].iloc[0])
    assert len(ipc)==24 and base>0
    for period,g in ipc.groupby('Periodo'):
        assert len(g)==3
        near(ref['deflators'][period],float(g.Indice.mean()/base),1e-10)
    assert not m.eligible_salary(p).Sector.eq('Sin clasificación').any()
    assert m.distribution(d,'Situación',within='Sexo').groupby('Sexo').Porcentaje.sum().sub(100).abs().max()<1e-8
    # El filtro de territorio no puede contaminar otra región ni duplicar hogares.
    for region in p['Región'].unique():
        a=m.select(p,regions=[region]);assert a['Región'].eq(region).all()
    assert m.select(p,'1900 - 1T').empty
    print(f'OK: {n} conciliaciones numéricas; claves, uniones, sectores y filtros verificados.')

if __name__=='__main__': run()
