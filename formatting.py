"""Unidades de presentación; los datos numéricos conservan su escala original."""
import re
import pandas as pd

PERCENT_COLUMNS = {'Porcentaje','Sin agua de red','Sin gas de red','Sin cloacas','Materiales insuficientes','Analfabetismo · 10+'}
COUNT_COLUMNS = {'Hogares ponderados','Personas ponderadas','Casos muestrales','Ponderación'}

def spanish(value, decimals=0):
    if pd.isna(value): return 'Sin datos'
    return f'{value:,.{decimals}f}'.replace(',','X').replace('.',',').replace('X','.')

def public_table(df):
    """Organiza los agregados por su comparación; no altera las medidas originales."""
    df=df.drop(columns=['Casos muestrales','Ponderación','NIVEL_ED'],errors='ignore').copy()
    units={}
    if {'Sexo','Situación','Porcentaje'}.issubset(df):
        df=df.pivot(index='Situación',columns='Sexo',values='Porcentaje')
        df=df.reindex([x for x in ['Ocupados','Desocupados','Inactivos','Sin información'] if x in df.index])
        df=df.reindex(columns=[c for c in ['Total','Mujer','Varón'] if c in df])
        units={c:'percent' for c in df};df=df.reset_index()
    elif {'Sexo','Nivel educativo','Ingreso'}.issubset(df):
        order=list(dict.fromkeys(df['Nivel educativo']))
        df=df.pivot(index='Nivel educativo',columns='Sexo',values='Ingreso').reindex(order)
        df=df.reindex(columns=[c for c in ['Total','Mujer','Varón'] if c in df])
        units={c:'money' for c in df};df=df.reset_index()
    elif {'Periodo','Indicador','Porcentaje'}.issubset(df):
        df=df.pivot(index='Periodo',columns='Indicador',values='Porcentaje').sort_index()
        df=df.reindex(columns=[c for c in ['Actividad','Empleo','Desocupación','Sin descuento jubilatorio'] if c in df])
        units={c:'percent' for c in df};df=df.reset_index()
    elif {'Periodo','Sector','Ingreso'}.issubset(df):
        df=df.pivot(index='Periodo',columns='Sector',values='Ingreso').sort_index()
        units={c:'money' for c in df};df=df.reset_index()
    else:
        # Las tablas de distribución aportan un total de control, sin sumar porcentajes de universos diferentes.
        count=next((c for c in ['Personas ponderadas','Hogares ponderados'] if c in df),None)
        labels=[c for c in df if c not in [count,'Porcentaje']]
        if count and 'Porcentaje' in df and len(labels)==1:
            total={labels[0]:'Total',count:df[count].sum(),'Porcentaje':df.Porcentaje.sum()}
            df=pd.concat([df,pd.DataFrame([total])],ignore_index=True)
    df.columns.name=None
    units.update({c:'percent' for c in df if c in PERCENT_COLUMNS})
    if 'Ingreso' in df: units['Ingreso']='money'
    df.attrs['units']=units
    return df


def display_table(df):
    df=public_table(df)
    formats={}
    for c in df.columns:
        unit=df.attrs['units'].get(c)
        if unit=='percent': formats[c]=lambda x: spanish(x,1)+' %' if pd.notna(x) else 'Sin datos'
        elif unit=='money': formats[c]=lambda x: '$ '+spanish(x) if pd.notna(x) else 'Sin datos'
        elif c in COUNT_COLUMNS or c=='Decil': formats[c]=spanish
    styled=df.style.format(formats,na_rep='Sin datos')
    if 'Total' in df: styled=styled.set_properties(subset=['Total'],**{'background-color':'#f5f5f2'})
    return styled


def export_table(df):
    df=public_table(df)
    names={c:c+(' (%)' if unit=='percent' else ' ($ ARS, dic. 2025)') for c,unit in df.attrs['units'].items()}
    return df.rename(columns=names)


def format_chart(fig,df):
    unit='percent' if 'Porcentaje' in df else 'money' if 'Ingreso' in df else None
    fig.update_layout(separators=',.')
    if not unit: return fig
    for t in fig.data:
        if t.type=='pie':
            t.update(texttemplate='%{value:.1f} %',hovertemplate='%{label}<br>%{value:.1f} %<extra></extra>')
            continue
        horizontal=getattr(t,'orientation',None)=='h'
        axis='x' if horizontal else 'y'
        t_axis=getattr(t,axis+'axis',None) or axis
        layout_axis=axis+'axis'+t_axis[1:]
        options=dict(tickformat='.1f' if unit=='percent' else ',.0f',ticksuffix=' %' if unit=='percent' else '',tickprefix='$ ' if unit=='money' else '')
        fig.update_layout(**{layout_axis:options})
        template=getattr(t,'hovertemplate',None) or ''
        value='%{'+axis+(':.1f} %' if unit=='percent' else ':,.0f}')
        if unit=='money': value='$ '+value
        template=re.sub(r'%\{'+axis+r'(?::[^}]*)?\}',lambda _:value,template)
        if unit=='money': template=template.replace('Ingreso=','Ingreso (ARS constantes)=')
        if 'Casos muestrales' in template:
            template=re.sub(r'%\{customdata\[0\](?::[^}]*)?\}', '%{customdata[0]:,.0f}',template)
        if template: t.hovertemplate=template
        if t.type=='bar': t.texttemplate=value
    return fig
