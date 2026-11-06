from pathlib import Path
import json
import html
import textwrap
import pandas as pd
import charts as charts
import streamlit as st
import metrics as m
from formatting import display_table, export_table
from ui import icon, metric_cards, CHART_ICONS

st.set_page_config(page_title='EPH | Análisis socioeconómico',page_icon='📊',layout='wide')
st.markdown('<style>'+Path(__file__).with_name('editorial.css').read_text(encoding='utf-8')+'</style>',unsafe_allow_html=True)
PAGES=['Vivienda y servicios','Educación','Mercado de trabajo','Composición del mercado laboral','Empleo por sector de actividad','Ingresos y distribución','Evolución del ingreso laboral']
@st.cache_data(show_spinner='Cargando bases oficiales de la EPH…')
def data(source_version): return m.load_data()
try: p,h,ref=data((m.ROOT/'data/reference.json').stat().st_mtime_ns)
except Exception as e:
    st.error('No se pudieron cargar los datos. Verificá que estén disponibles las bases oficiales y sus referencias.');st.stop()

SECTIONS = ['Panorama','Condiciones de vida','Trabajo','Ingresos']
VIEWS = {
 'Condiciones de vida': {'Vivienda y servicios':PAGES[0], 'Educación':PAGES[1]},
 'Trabajo': {'Participación y evolución':PAGES[2], 'Composición del empleo':PAGES[3], 'Sectores de actividad':PAGES[4]},
 'Ingresos': {'Distribución y brechas':PAGES[5], 'Evolución por sector':PAGES[6]},
}
price_base = ref['price_base']
periods = sorted(p.Periodo.unique())
coverage = ' a '.join(f'{period[-2:]} {period[:4]}' for period in dict.fromkeys([periods[0], periods[-1]]))
st.markdown(
    '<div class="eph-appbar"><div class="eph-appbar-brand"><span class="eph-appmark">'+icon('chart')+'</span>'
    '<div><h1>Análisis socioeconómico de la EPH</h1>'
    f'<div class="eph-appbar-subtitle">EPH {coverage} · 31 aglomerados urbanos</div></div></div>'
    '<div class="eph-appbar-meta"><span>'+icon('pin')+'Microdatos del INDEC</span></div></div>',
    unsafe_allow_html=True)

def reset_filters():
    for k in ['regions','cities','sexes']: st.session_state[k]=[]

def prune_cities():
    valid=set(m.select(p,regions=st.session_state.get('regions',[])).Aglomerado)
    st.session_state['cities']=[x for x in st.session_state.get('cities',[]) if x in valid]

unit='Personas';territory='Región';sectors=None
if st.session_state.get('section') not in SECTIONS:
    st.session_state['section']='Condiciones de vida' if st.session_state.get('section')=='Vida cotidiana' else 'Panorama'
with st.container(key='explorer'):
    with st.container(key='app_toolbar'):
        nav,period_control,filter_control=st.columns([4.6,1.15,.8],vertical_alignment='center',gap='small')
        with nav:
            section=st.segmented_control('Área',SECTIONS,format_func=lambda x: ':material/'+{'Panorama':'space_dashboard','Condiciones de vida':'home','Trabajo':'work_outline','Ingresos':'payments'}[x]+': '+x,required=True,key='section',label_visibility='collapsed',width='stretch',wrap=True) or 'Panorama'
        with period_control:
            period=st.selectbox('Período',periods,index=len(periods)-1,key='period',label_visibility='collapsed')
        count=sum(len(st.session_state.get(k,[])) for k in ['regions','cities','sexes'])
        with filter_control:
            with st.popover('Filtros'+(f' · {count}' if count else ''),icon=':material/tune:',width='stretch'):
                regions=st.multiselect('Región',sorted(p['Región'].unique()),key='regions',on_change=prune_cities)
                available=m.select(p,regions=regions)
                cities=st.multiselect('Aglomerado',sorted(available.Aglomerado.unique()),key='cities')
                sexes=st.multiselect('Sexo · indicadores de personas',['Mujer','Varón'],key='sexes')
                st.caption('Sin selección se incluyen todas las categorías. El sexo solo filtra indicadores de personas.')
                st.button('Limpiar filtros',icon=':material/restart_alt:',on_click=reset_filters,width='stretch')
    page=None
    if section!='Panorama':
        with st.container(key='view_controls'):
            secondary=st.columns([2.5,1,1] if section=='Condiciones de vida' else [1],vertical_alignment='center',gap='small')
            with secondary[0]:
                labels=list(VIEWS[section])
                view=st.segmented_control('Vista',labels,default=labels[0],required=True,key='view_'+section,label_visibility='collapsed',width='content',wrap=True)
                page=VIEWS[section][view]
            if page==PAGES[0]:
                with secondary[1]:unit=st.selectbox('Unidad estadística',['Personas','Hogares'],key='housing_unit',label_visibility='collapsed')
                with secondary[2]:territory=st.selectbox('Desagregación',['Región','Aglomerado'],key='housing_territory',label_visibility='collapsed')
    if page==PAGES[6]:
        salary_history=m.select(p,None,regions,cities,sexes)
        options=sorted(m.eligible_salary(salary_history).Sector.unique())
        sectors=st.multiselect('Sectores a comparar',options,default=[s for s in charts.DEFAULT_SECTORS if s in options],key='income_sectors')
    scope=' / '.join(regions+cities) if regions or cities else '31 aglomerados urbanos'
    st.markdown('<div class="eph-scope">'+icon('pin')+html.escape(scope+(' · '+', '.join(sexes) if sexes else '')+' · INDEC, EPH')+'</div>',unsafe_allow_html=True)

pt=m.select(p,period,regions,cities,sexes)
pt_total=m.select(p,period,regions,cities)
ht=m.select(h,period,regions,cities)
history=m.select(p,None,regions,cities,sexes)
if pt.empty or ht.empty:
    st.info('No hay observaciones para esta selección. Ajustá los filtros.');st.stop()

def metric_grid(values):
    st.markdown(metric_cards(values, price_base),unsafe_allow_html=True)

# Las figuras se construyen en charts.py, compartido con exploracion_eph.py.
view_name='Panorama' if section=='Panorama' else page
if page==PAGES[0] and unit=='Hogares' and sexes:
    st.caption('El filtro de sexo no se aplica a hogares.')
if page==PAGES[6] and not sectors:
    st.info('Seleccioná al menos un sector para comparar.');st.stop()

values=charts.cards(view_name,pt,ht,ref,period)

if values: metric_grid(values)
if view_name in ['Panorama',PAGES[5]]:
    income_context = f'Ingresos a precios de {price_base} · IPCF medio entre hogares.'
    if sexes: income_context+=' El filtro de sexo no se aplica a hogares.'
    st.caption(income_context)
try:
    specs=charts.build(view_name,pt,ht,history,ref,period,unit,territory,sectors,population=pt_total)
except ValueError as e:
    st.error(str(e));st.stop()
def render_table(spec):
    table=display_table(spec.rows)
    config={}
    if len(table.data.columns) and table.data.columns[0] not in ['Periodo','Decil']:
        config[table.data.columns[0]]=st.column_config.Column(width='medium')
    for col in table.data.columns:
        if col=='Personas ponderadas':config[col]=st.column_config.Column('Personas',width='small',help='Estimación poblacional ponderada, no cantidad de encuestas.')
        elif col=='Hogares ponderados':config[col]=st.column_config.Column('Hogares',width='small',help='Estimación de hogares ponderada, no cantidad de encuestas.')
        elif col=='Porcentaje':config[col]=st.column_config.Column('%',width='small')
        elif col in ['Periodo','Decil']:config[col]=st.column_config.Column(col,width='small')
        elif col in ['Actividad','Empleo','Desocupación','Sin descuento jubilatorio']:
            label={'Desocupación':'Desocup.','Sin descuento jubilatorio':'Sin desc.'}.get(col,col)
            config[col]=st.column_config.Column(label,width='small',help=col)
    with st.container(key='data_'+spec.identity):
        with st.container(key='table_tools_'+spec.identity):
            label,download=st.columns([4,1],vertical_alignment='center',gap='small')
            with label:
                if 'Ingreso' in spec.rows:
                    table_label = f'Datos · Pesos de {price_base}'
                elif spec.identity in {'dwelling', 'tenure', 'housing'}:
                    table_label = f'Datos · {unit}'
                elif spec.identity in {'overview_services', 'education', 'secondary', 'status_sex', 'population', 'inactivity', 'occupation', 'sectors'}:
                    table_label = 'Datos · Personas'
                else:
                    table_label = 'Datos del gráfico'
                st.markdown('<div class="eph-table-label">'+icon('table')+table_label+'</div>',unsafe_allow_html=True)
            with download:
                st.download_button('CSV',icon=':material/download:',type='tertiary',data=export_table(spec.rows, price_base).to_csv(index=False,decimal=',',sep=';').encode('utf-8-sig'),file_name=f'eph_{spec.identity}_{period}.csv',mime='text/csv',key='download_'+spec.identity,width='content')
        st.dataframe(table,width='stretch',hide_index=True,row_height=30,column_config=config)

for spec in specs:
    with st.container(key='panel_'+spec.identity):
        st.markdown('<div class="eph-chart-heading"><span class="eph-chart-icon">'+icon(CHART_ICONS.get(spec.identity,'chart'))+'</span><h3>'+html.escape(spec.title)+'</h3></div>',unsafe_allow_html=True)
        if 'Ingreso' in spec.rows:
            universe = 'PEA con ingresos · ' if spec.identity == 'income_education' else ''
            st.markdown(
                f'<div class="eph-unit">{universe}Pesos de {html.escape(price_base)} · Ajustados por IPC nacional</div>',
                unsafe_allow_html=True,
            )
        def render_figure():
            st.plotly_chart(spec.figure,width='stretch',key=spec.identity,config={'responsive':True,'displayModeBar':False,'scrollZoom':False})
            st.caption(spec.note)
            if 'Casos muestrales' in spec.rows and spec.rows['Casos muestrales'].between(1,9).any():
                st.warning('Hay estimaciones con una base reducida de observaciones; interpretalas con cautela.')
        if spec.figure is not None and spec.identity not in ['income_history','income_education']:
            with st.container(key='plot_table_'+spec.identity):
                visual,details=st.columns([1.6,1],gap='medium')
                with visual:render_figure()
                with details:render_table(spec)
        elif spec.figure is not None:
            render_figure();render_table(spec)
        elif spec.rows.empty:
            st.info(spec.note)
        else:
            st.caption(spec.note);render_table(spec)
if section=='Panorama':
    st.subheader('Seguí explorando')
    def navigate(destination): st.session_state['section']=destination
    for col,destination,label in zip(st.columns(3),SECTIONS[1:],['Vivienda y educación','Participación y empleo','Ingresos y brechas']):
        col.button(label,icon={'Condiciones de vida':':material/home:','Trabajo':':material/work_outline:','Ingresos':':material/payments:'}[destination],on_click=navigate,args=(destination,),width='stretch')

with st.expander('Fuentes y metodología',icon=':material/menu_book:'):
    st.markdown('[Mercado de trabajo · INDEC](https://www.indec.gob.ar/uploads/informesdeprensa/mercado_trabajo_eph_2trim26433FCBC5A8.pdf) · [Condiciones de vida · INDEC](https://www.indec.gob.ar/uploads/informesdeprensa/eph_indicadores_hogares_11_269E1CF84248.pdf) · [Encuesta Permanente de Hogares · INDEC](https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos-1) · [Distribución del ingreso · INDEC](https://www.indec.gob.ar/uploads/informesdeprensa/ingresos2trim26B36ABAB2C6.pdf)')
    st.write('Cobertura: 31 aglomerados urbanos. Las estimaciones se recalculan para la población y el período seleccionados, con los ponderadores específicos de cada indicador.')
    st.write('Para los ingresos a precios constantes se usa el IPC nacional promedio de tres meses con un mes de rezago. Por ejemplo, el segundo trimestre usa marzo, abril y mayo. El IPCF se promedia entre hogares; el ingreso laboral corresponde a asalariados ocupados con ingresos positivos. Las notas de cada gráfico detallan su universo.')

st.markdown('<div class="eph-footer">'+icon('table')+f'<span>Elaboración propia en base a INDEC · Encuesta Permanente de Hogares.<br>31 aglomerados urbanos · Ingresos expresados a precios de {html.escape(price_base)}.</span></div>',unsafe_allow_html=True)
