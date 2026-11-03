from pathlib import Path
from streamlit.testing.v1 import AppTest

at=AppTest.from_file(str(Path(__file__).with_name('app.py')),default_timeout=90).run()
def check(label):
    assert not at.exception,(label,[e.message for e in at.exception])
    assert not at.error,(label,[e.value for e in at.error])
    assert all(e.label!='Datos y definición' for e in at.expander), 'Las tablas deben permanecer visibles'
    print('OK:',label)
check('Panorama inicial')
for section in ['Condiciones de vida','Trabajo','Ingresos']:
    at.button_group(key='section').set_value(section).run()
    key='view_'+section
    for view in list(at.button_group(key=key).options):
        at.button_group(key=key).set_value(view).run()
        check(section+' / '+view)

at.button_group(key='section').set_value('Condiciones de vida').run()
at.button_group(key='view_Condiciones de vida').set_value('Vivienda y servicios').run()
at.selectbox(key='housing_unit').set_value('Hogares').run()
at.selectbox(key='housing_territory').set_value('Aglomerado').run()
check('Unidad hogares y desagregación por aglomerado')
assert len(at.get('plotly_chart'))>0

at.multiselect(key='regions').set_value(['Cuyo']).run()
city=at.multiselect(key='cities').options[0]
at.multiselect(key='cities').set_value([city]).run()
at.multiselect(key='sexes').set_value(['Mujer']).run()
at.button_group(key='section').set_value('Panorama').run()
check('Filtros conservados al navegar')
assert at.multiselect(key='regions').value==['Cuyo']
assert at.multiselect(key='sexes').value==['Mujer']
at.multiselect(key='regions').set_value(['Pampeana']).run()
assert at.multiselect(key='cities').value==[]
check('Aglomerados incompatibles se limpian al cambiar región')
next(b for b in at.button if b.label=='Limpiar filtros').click().run()
assert at.multiselect(key='regions').value==[]
next(b for b in at.button if b.label=='Ingresos y brechas').click().run()
assert at.button_group(key='section').value=='Ingresos'
at.button_group(key='view_Ingresos').set_value('Evolución por sector').run()
at.multiselect(key='income_sectors').set_value([]).run()
check('Navegación desde el panorama y selección vacía')
assert len(at.info)>0
print('OK: cuatro áreas, siete vistas de detalle y filtros compartidos.')
