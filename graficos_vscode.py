# %% [markdown]
# # EPH: exploración dentro de VS Code
# Ejecutar celdas con Ejecutar celda o Shift+Enter; elegir el kernel .venv.
# Las figuras aparecen en la ventana interactiva como en un notebook.
# charts.py es la única implementación, compartida con la web.
# Este archivo no publica datos ni abre un navegador.

# %% Preparación: ejecutar una vez por sesión
from pathlib import Path
import sys
import plotly.io as pio
from IPython.display import display, Markdown
ROOT=Path(__file__).resolve().parent if '__file__' in globals() else Path.cwd()
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import metrics as m
import charts
from formatting import display_table
pio.renderers.default='plotly_mimetype'
p,h,ref=m.load_data()
print(f'Bases cargadas: {len(p):,} registros de personas, {len(h):,} de hogares.')

# %% Filtros: editar y volver a ejecutar para actualizar la selección
PERIODO = max(p.Periodo)        # Ejemplo: '2025 - 4T'
REGIONES=[]                 # Ejemplo: ['Cuyo']; vacío = todas
AGLOMERADOS=[]              # Ejemplo: ['Gran Córdoba']
SEXOS=[]                    # Ejemplo: ['Mujer']; solo personas
UNIDAD='Personas'           # 'Personas' o 'Hogares'
TERRITORIO='Región'         # 'Región' o 'Aglomerado'
SECTORES=charts.DEFAULT_SECTORS
pt=m.select(p,PERIODO,REGIONES,AGLOMERADOS,SEXOS)
pt_total=m.select(p,PERIODO,REGIONES,AGLOMERADOS)
ht=m.select(h,PERIODO,REGIONES,AGLOMERADOS)
history=m.select(p,None,REGIONES,AGLOMERADOS,SEXOS)
if pt.empty or ht.empty: raise ValueError('No hay datos para estos filtros.')
def mostrar(view):
    display(Markdown('## '+view+' · '+PERIODO))
    for label,value in charts.cards(view,pt,ht,ref,PERIODO):
        unit = f" · Pesos de {ref['price_base']}" if value.startswith('$') else ''
        display(Markdown(f'**{label}:** {value}{unit}'))
    for spec in charts.build(view,pt,ht,history,ref,PERIODO,UNIDAD,TERRITORIO,SECTORES,population=pt_total):
        display(Markdown('### '+spec.title))
        if spec.figure is not None: display(spec.figure)
        elif not spec.rows.empty: display(display_table(spec.rows))
        display(Markdown(spec.note))

# %% Panorama
mostrar('Panorama')

# %% Condiciones de vida: vivienda, servicios y educación
mostrar('Vivienda y servicios')
mostrar('Educación')

# %% Trabajo: participación, composición y sectores
mostrar('Mercado de trabajo')
mostrar('Composición del mercado laboral')
mostrar('Empleo por sector de actividad')

# %% Ingresos: distribución, brechas y evolución por sector
mostrar('Ingresos y distribución')
mostrar('Evolución del ingreso laboral')
