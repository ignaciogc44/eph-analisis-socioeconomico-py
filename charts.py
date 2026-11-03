"""Única definición de datos, títulos y figuras para Streamlit y VS Code."""
from dataclasses import dataclass
import textwrap
import pandas as pd
import plotly.express as px
import metrics as m
from formatting import format_chart, spanish

PALETTE=['#F34B18','#101010','#8c8c88','#a57020','#176786','#b8b8b3','#89645d','#c49c74']
VIEWS=['Panorama','Vivienda y servicios','Educación','Mercado de trabajo','Composición del mercado laboral','Empleo por sector de actividad','Ingresos y distribución','Evolución del ingreso laboral']
DEFAULT_SECTORS=['Industria Manufacturera','Comercio','Construcción','Administración Pública','Enseñanza']

@dataclass
class Chart:
    identity: str
    title: str
    rows: pd.DataFrame
    note: str
    figure: object = None

def figure(rows,kind,**kwargs):
    kwargs.setdefault('color_discrete_sequence',PALETTE)
    f=getattr(px,kind)(rows,template='plotly_white',**kwargs)
    f.update_layout(font=dict(family='Arial, Helvetica, sans-serif',size=13,color='#101010'),paper_bgcolor='white',plot_bgcolor='white',legend_title_text='',hoverlabel=dict(bgcolor='white'),height=330,autosize=True,legend=dict(orientation='h',yanchor='top',y=-.18,x=0,entrywidth=0,entrywidthmode='pixels'),margin=dict(l=8,r=40,t=20,b=70),dragmode=False,bargap=.35)
    f.update_traces(cliponaxis=False,selector=dict(type='bar'))
    format_chart(f,rows)
    if kind=='bar' and kwargs.get('orientation')=='h':
        label=kwargs['y'];labels=list(dict.fromkeys(rows[label].dropna()))
        short_names={'Superior/universitario incompleto': 'Superior/univ. incompleto', 'Superior/universitario completo': 'Superior/univ. completo', 'Agricultura, Ganadería, Caza, Silvicultura y Pesca': 'Agro y pesca', 'Suministro de Electricidad, Gas, Vapor y Aire Acondicionado': 'Electricidad y gas', 'Suministro de Agua; Alcantarillado, Gestión de Desechos': 'Agua y saneamiento', 'Hogares como empleadores': 'Servicio doméstico', 'Trabajador familiar sin remuneración': 'Familiar sin remuneración'}
        ticks=['<br>'.join(textwrap.wrap(short_names.get(str(x),str(x)),22)) for x in labels]
        f.update_layout(yaxis=dict(autorange='reversed',title=None,tickmode='array',tickvals=labels,ticktext=ticks,tickfont=dict(size=11)),xaxis_title=None,height=max(260,34*len(labels)+86))
    f.update_xaxes(showline=True,linecolor='#bebeba',ticks='',tickfont=dict(color='#777777',size=11),showgrid=False,nticks=5)
    f.update_yaxes(showline=False,ticks='',tickfont=dict(color='#777777',size=11),gridcolor='#e8e8e5',gridwidth=.7,zeroline=False,nticks=5)
    if kind=='line':
        f.update_traces(line=dict(width=2.8),marker=dict(size=6))
        f.update_xaxes(title_text='')
        if 'Periodo' in rows:
            periods=list(dict.fromkeys(rows.Periodo))
            chosen=[periods[round(i*(len(periods)-1)/3)] for i in range(4)] if len(periods)>4 else periods
            f.update_xaxes(tickmode='array',tickvals=chosen,ticktext=[x[-2:]+' '+x[2:4] for x in chosen],tickangle=0)
        f.update_yaxes(title_text='')
    if kind=='bar' and kwargs.get('orientation')=='h':
        f.update_xaxes(showgrid=True,gridcolor='#e8e8e5',zeroline=False)
        f.update_yaxes(showgrid=False,nticks=None)
    if 'Ingreso' in rows:
        for trace in f.data:
            axis='x' if getattr(trace,'orientation',None)=='h' else 'y'
            if trace.type=='bar':
                vals=getattr(trace,axis)
                trace.text=[('$ '+spanish(v/1e6,2)+' M') if pd.notna(v) and abs(v)>=1e6 else ('$ '+spanish(v/1000,0)+' mil') if pd.notna(v) and abs(v)>=1000 else ('$ '+spanish(v)) if pd.notna(v) else '' for v in vals]
                trace.texttemplate='%{text}'
                trace.textposition='outside' if axis=='x' else 'none'
                trace.textfont=dict(size=11)
            if axis=='x': f.update_xaxes(tickformat='.2s',nticks=4)
            else: f.update_yaxes(tickformat='.2s',nticks=5)
    if kind=='bar' and 'Decil' in rows:
        f.update_xaxes(tickmode='array',tickvals=list(range(1,11)),ticktext=[str(x) for x in range(1,11)],title_text='Decil de hogares')
        f.update_yaxes(title_text='')
    if kind=='line':
        rate_colors={'Actividad':'#101010','Empleo':'#9c9c97','Desocupación':'#F34B18','Sin descuento jubilatorio':'#a57020'}
        for trace in f.data:
            if trace.name in rate_colors: trace.line.color=rate_colors[trace.name];trace.marker.color=rate_colors[trace.name]
    if kind=='bar' and 'Sexo' in rows and 'Ingreso' in rows:
        f.update_layout(height=max(280,40*len(rows['Nivel educativo'].unique())+86),legend=dict(entrywidth=0,entrywidthmode='pixels',xref='paper',x=0,xanchor='left'))
        f.update_traces(text=None,texttemplate=None,textposition='none')
    if kind=='line' and 'Sector' in rows:
        names={'Administración Pública':'Adm. pública','Industria Manufacturera':'Industria manufacturera'}
        for trace in f.data:
            trace.name=names.get(trace.name,trace.name)
        f.update_layout(margin=dict(b=90))
    for trace in f.data:
        if trace.name and len(trace.name)>30: trace.name=trace.name[:28]+'…'
    return f

def cards(view,p,h,ref,period):
    rows=[]
    if view in ['Panorama','Mercado de trabajo']:
        values=m.rates(p)
        rows=[(k,spanish(v,1)+' %') for k,v in values.items() if view!='Panorama' or k!='Sin descuento jubilatorio']
    if view in ['Panorama','Ingresos y distribución']:
        factor=ref['deflators'].get(period)
        if factor:
            rows += [('Ingreso laboral · asalariados con ingresos','$ '+spanish(m.mean(m.eligible_salary(p),'P21','PONDIIO')/factor)),('IPCF medio entre hogares','$ '+spanish(m.mean(h,'IPCF','PONDIH')/factor))]
    if view=='Panorama':
        a=p.loc[p.CH06.ge(18)];rows += [('Secundaria finalizada · 18+',spanish(m.share(a,a.NIVEL_ED.isin([4,5,6])),1)+' %')]
    return rows

def build(view,p,h,history,ref,period,unit='Personas',territory='Región',sectors=None,population=None):
    specs=[]
    population=p if population is None else population
    def chart(identity,title,rows,note,kind=None,**kwargs):
        if 'Ingreso' in rows and 'Pesos de diciembre de 2025' not in note:
            note='Pesos de diciembre de 2025. '+note
        specs.append(Chart(identity,title,rows,note,figure(rows,kind,**kwargs) if kind else None))
    def bars(identity,title,rows,label,note,value='Porcentaje',color=None):
        chart(identity,title,rows,note,'bar',x=value,y=label,color=color,orientation='h',barmode='group',color_discrete_map={'Total':'#8c8c88','Mujer':'#F34B18','Varón':'#101010'},category_orders={'Sexo':['Total','Mujer','Varón']})
    if view in ['Panorama','Mercado de trabajo']:
        df=pd.DataFrame([{'Periodo':name}|m.rates(g) for name,g in history.groupby('Periodo')])
        cols=['Actividad','Empleo','Desocupación'] if view=='Panorama' else list(m.rates(p))
        df=df.melt('Periodo',value_vars=cols,var_name='Indicador',value_name='Porcentaje')
        chart('labor_history','Evolución de las tasas',df,'Actividad y empleo: población total. Desocupación: PEA. Sin descuento jubilatorio: asalariados ocupados con respuesta válida; no equivale a informalidad total. La historia conserva territorio y sexo.','line',x='Periodo',y='Porcentaje',color='Indicador',markers=True)
        if view=='Panorama':
            df=pd.DataFrame(m.housing_summary(p).items(),columns=['Condición','Porcentaje'])
            bars('overview_services','Acceso a servicios en la vivienda',df,'Condición','Personas, ponderación PONDERA. Materiales incluye parcialmente insuficientes.')
        else:
            chart('population','Composición de la población',m.distribution(p,'Estado detallado'),'Población total, ponderación PONDERA.')
    elif view=='Vivienda y servicios':
        d=p if unit=='Personas' else h
        for identity,title,label in [('dwelling','Tipo de vivienda','Tipo de vivienda'),('tenure','Régimen de tenencia','Tenencia')]:
            rows=m.distribution(d,label).sort_values('Porcentaje',ascending=False)
            if unit=='Hogares': rows=rows.rename(columns={'Personas ponderadas':'Hogares ponderados'})
            note=f'{unit}, ponderación PONDERA. Incluye todas las categorías.'
            if identity=='tenure': note+=' Ocupantes: pago de impuestos/expensas, relación de dependencia, permiso o de hecho (II7=4 a 7). En sucesión se presenta por separado.'
            bars(identity,title,rows,label,note)
        rows=[]
        for name,g in d.groupby(territory):
            a=p.loc[p[territory].eq(name)&p.CH06.ge(10)]
            rows.append({territory:name}|m.housing_summary(g)|{'Analfabetismo · 10+':m.share(a,a.CH09.eq(2))})
        chart('housing','Servicios y condiciones por territorio',pd.DataFrame(rows),'Porcentajes. Analfabetismo: personas de 10 años o más. Materiales incluye parcialmente insuficientes. El informe del INDEC es semestral y estos indicadores son trimestrales.')
    elif view=='Educación':
        d=p.loc[p.CH06.ge(18)].copy();df=m.distribution(d,'Nivel educativo')
        order={v:i for i,v in enumerate(m.EDUCATION.values())}
        df=df.assign(orden=df['Nivel educativo'].map(order)).sort_values('orden').drop(columns='orden')
        bars('education','Nivel educativo alcanzado',df,'Nivel educativo','Personas de 18 años o más, ponderación PONDERA.')
        d['Finalización']=d.NIVEL_ED.isin([4,5,6]).map({True:'Finalizó secundaria',False:'No finalizó secundaria'})
        df=m.distribution(d,'Finalización')
        chart('secondary','Secundaria finalizada',df,'Personas de 18 años o más. Incluye quienes cursan o finalizaron estudios superiores.','pie',names='Finalización',values='Porcentaje',hole=.65)
    elif view=='Composición del mercado laboral':
        df=m.distribution(p,'Situación',within='Sexo')
        overall=m.distribution(population,'Situación').assign(Sexo='Total')
        df=pd.concat([overall,df],ignore_index=True)
        chart('status_sex','Situación de actividad por sexo',df,'Total incluye ambos sexos del mismo período y territorio, aunque se filtre un sexo. Cada columna suma 100%. Desocupados es porcentaje de la población de cada sexo, no tasa sobre la PEA. Sin información separa las entrevistas no realizadas.','bar',x='Porcentaje',y='Sexo',color='Situación',orientation='h',barmode='stack',category_orders={'Sexo':['Total','Mujer','Varón']})
        for identity,title,label,d in [
            ('inactivity','Categorías de inactividad · 10 años o más','Categoría de inactividad',p.loc[p.ESTADO.eq(3)&p['Categoría de inactividad'].notna()]),
            ('occupation','Categoría ocupacional · ocupados','Categoría ocupacional',p.loc[p.ESTADO.eq(1)&p['Categoría ocupacional'].notna()])]:
            bars(identity,title,m.distribution(d,label).sort_values('Porcentaje',ascending=False),label,'Ponderación PONDERA; categorías válidas dentro del universo indicado. Los porcentajes pueden no sumar 100% por redondeo.')
    elif view=='Empleo por sector de actividad':
        bars('sectors','Distribución de ocupados por sector',m.distribution(p.loc[p.ESTADO.eq(1)],'Sector').sort_values('Porcentaje',ascending=False),'Sector','Ocupados, ponderación PONDERA. Clasificación CAES; actividad no especificada permanece en el total.')
    elif view=='Ingresos y distribución':
        if period not in ref['deflators']: raise ValueError('No hay IPC de referencia para este período.')
        df=m.grouped_income(h.loc[h.DECCFR.between(1,10)],['DECCFR'],'IPCF','PONDIH',ref).rename(columns={'DECCFR':'Decil'})
        chart('deciles','IPCF medio de hogares por decil de hogares',df,'Media del IPCF entre hogares, ponderada por PONDIH. No equivale al promedio por personas del cuadro 9 del INDEC. Deciles nacionales originales de la EPH: los filtros no recalculan los cortes. Pesos de diciembre de 2025; IPC nacional medio del trimestre.','bar',x='Decil',y='Ingreso')
        df=m.grouped_income(m.eligible_individual(p),['NIVEL_ED','Sexo'],'P47T','PONDII',ref)
        overall=m.grouped_income(m.eligible_individual(population),['NIVEL_ED'],'P47T','PONDII',ref).assign(Sexo='Total')
        df=pd.concat([overall,df],ignore_index=True)
        df['Nivel educativo']=df.NIVEL_ED.map(m.EDUCATION).fillna('Sin información')
        df=df.assign(orden=df.NIVEL_ED.map({v:i for i,v in enumerate(m.EDUCATION)})).sort_values('orden').drop(columns='orden')
        bars('income_education','Ingreso total individual · PEA con ingresos · educación y sexo',df,'Nivel educativo','Total incluye ambos sexos del mismo período y territorio, aunque se filtre un sexo. PEA con P47T positivo; ponderación PONDII. Incluye fuentes laborales y no laborales; sin corte etario adicional. Pesos constantes ajustados por IPC nacional.',value='Ingreso',color='Sexo')
    elif view=='Evolución del ingreso laboral':
        sectors=DEFAULT_SECTORS if sectors is None else sectors
        if not sectors: return []
        d=m.eligible_salary(history);d=d.loc[d.Sector.isin(sectors)]
        df=m.grouped_income(d,['Periodo','Sector'],'P21','PONDIIO',ref)
        grid=pd.MultiIndex.from_product([sorted(history.Periodo.unique()),sectors],names=['Periodo','Sector']).to_frame(index=False)
        df=grid.merge(df,on=['Periodo','Sector'],how='left')
        chart('income_history','Ingreso medio de asalariados con ingresos por rama',df,'Asalariados ocupados con P21 positivo, ponderación PONDIIO. Pesos constantes ajustados por IPC nacional. Períodos sin observaciones mantienen huecos. Las ramas con pocos casos requieren cautela.','line',x='Periodo',y='Ingreso',color='Sector',markers=True)
    return specs
