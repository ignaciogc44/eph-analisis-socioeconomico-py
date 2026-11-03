# Auditoría del tablero EPH

Fecha de revisión: 3 de noviembre de 2026. Alcance: proyecto local, instantánea 2024–2025. No se publicó ni se desplegó una aplicación remota.

## Datos y tablas

Se verificaron 138 tablas en ocho trimestres mediante 6.038 comprobaciones numéricas y de integridad. El recálculo lee los TXT oficiales y reconstruye porcentajes, medias y agrupaciones sin llamar a los helpers de cálculo de `metrics.py`. Incluye vivienda para personas y hogares, regiones y aglomerados, educación 18+, alfabetismo 10+, composición laboral, sectores, ingresos por educación y sexo, deciles de hogares y series de ingreso por rama. También pasaron las 243 conciliaciones previas de `validar.py`.

La clasificación CAES y los nombres territoriales se reutilizan del catálogo previamente revisado: esta ejecución no verifica de forma independiente cada código de ese catálogo. No se probaron todas las combinaciones posibles de filtros ni se estimaron intervalos de confianza para cada celda.

Fuentes de contraste:

- [Mercado de trabajo, 4T2025, cuadros 1.1 y 1.5](https://www.indec.gob.ar/uploads/informesdeprensa/mercado_trabajo_eph_4trim25AF451E16DE.pdf).
- [Distribución del ingreso, 4T2025, cuadros 3, 4, 6.1 y 9](https://biblioteca.indec.gob.ar/bases/minde/ingresos4trim25.pdf).
- [Condiciones de vida, 2S2025 y anexo metodológico](https://www.indec.gob.ar/uploads/informesdeprensa/eph_indicadores_hogares_04_266C2447C938.pdf).
- Diccionario oficial de la base EPH: codificación II7, CAT_OCUP, CAT_INAC y ponderadores. Los TXT locales se contrastaron con sus SHA-256 del manifiesto conservado; esta ejecución no volvió a descargar todos los archivos.

### Correcciones aplicadas

- Todas las tablas de respaldo se muestran directamente, sin un desplegable que las oculte.
- II7=5 es ocupante en relación de dependencia: ahora se integra a Ocupante junto con II7=4, 6 y 7. II7=8 es En sucesión y se muestra por separado. En 4T2025, base personas: Ocupante 10,0%, En sucesión 0,9%, Otros 0,2%. No cambia el total poblacional.
- En base hogares, la columna de expansión se llama Hogares ponderados.
- Los deciles conservan los cortes nacionales oficiales; filtrar por región o sexo no genera nuevos deciles.
- Se conserva el aviso de que los porcentajes pueden no sumar 100% por redondeo. En ocupación, 71,5 + 24,7 + 3,3 + 0,4 = 99,9 por esa razón; no es un error.

### Diferencias metodológicas que se conservan

- Vivienda: el tablero es trimestral; el informe de condiciones de vida es semestral. También debe igualarse la unidad personas/hogares y las exclusiones de población para comparar.
- Educación del tablero: personas de 18 años o más. El informe oficial presenta otras aperturas etarias; no corresponde forzar coincidencia entre universos diferentes.
- Ingreso individual por educación: PEA con P47T positivo, PONDII, sin corte etario adicional. Es una elaboración propia con microdatos, no un cuadro publicado con esas mismas aperturas.
- Ingreso laboral: ocupados asalariados con P21 positivo y PONDIIO. El nominal 4T2025 redondea a $1.082.635 y coincide con INDEC. El tablero expresa $1.111.838 a precios de diciembre de 2025.
- IPCF: promedio entre hogares con PONDIH; no es el promedio ponderado por personas. Los deciles seleccionan hogares con ingresos; la tarjeta general también contempla los hogares sin ingresos con ponderación válida.
- El ajuste usa IPC nacional medio del trimestre / IPC diciembre de 2025. Es una aproximación: los ingresos se refieren al mes anterior a la entrevista. No se modifica esa política por esta auditoría.
- Sin descuento jubilatorio entre asalariados no equivale a la informalidad del conjunto de ocupados.

## Seguridad y publicación

Resultado: no se detectaron credenciales incrustadas ni hallazgos críticos en el alcance local revisado. Esto no garantiza ausencia de vulnerabilidades ni sustituye una revisión del alojamiento futuro.

- Se escanearon archivos de código, configuración, documentación y referencias, excluyendo el entorno de terceros y los microdatos. El control busca formatos comunes de tokens, claves privadas, secretos literales, rutas personales y ejecución dinámica. No se imprimen posibles valores sensibles.
- Diez ejemplos de archivos sensibles/microdatos fueron comprobados con `git check-ignore` en un repositorio temporal. En la revisión inicial no había un repositorio Git ni historial local que revisar. El primer commit se revisa por separado antes de su publicación.
- `.gitignore` excluye secretos de Streamlit, `.env`, certificados, entornos, microdatos, respuestas API y notebooks con posibles salidas locales. El archivo `.py` de celdas de VS Code permanece publicable.
- `pip-audit` revisó las versiones de `requirements-lock.txt` con la base de avisos de PyPI y no informó vulnerabilidades conocidas. El resultado se conserva en `auditoria_dependencias.json`. `pip check` no informó conflictos. La base de avisos no detecta vulnerabilidades desconocidas ni asegura la integridad de cada distribución instalada; el lock actual fija versiones sin hashes.
- Se revisaron los flujos de descarga y exportación: orígenes HTTPS de INDEC; API opcional con token desde entorno; extracción ZIP mediante nombres base, sin `extractall`; exportación de agregados sin identificadores de hogares/personas. Las descargas son utilidades administrativas locales, no endpoints expuestos al visitante.
- No hay subida de archivos, ejecución de código aportado por el visitante, consultas SQL ni edición remota de archivos en la interfaz.
- El HTML propio escapa los valores dinámicos. Se conservan CORS y XSRF activos, servicio de archivos estáticos deshabilitado y escucha local en 127.0.0.1. Se ocultaron detalles técnicos de errores al visitante.
- Se fijó la versión de Streamlit usada y probada para evitar que el mínimo anterior instalara una interfaz incompatible.

Antes de publicar: revisar el diff/listado exacto del primer commit, atribuir las fuentes y decidir la licencia del código. Antes de alojar una demo: revisar HTTPS, configuración del proveedor, límites de recursos y protección contra abuso. No hace falta autenticar a visitantes si la demo solo ofrece estos agregados públicos. No habilitar acceso a archivos personales o secretos del equipo.

En GitHub conviene activar revisión de dependencias y protección contra secretos. [Documentación de GitHub](https://docs.github.com/en/code-security/concepts/secret-security/push-protection). Los secretos del alojamiento se configuran fuera del código: [documentación de Streamlit](https://docs.streamlit.io/deploy/concepts/secrets).

## Comprobaciones ejecutables

```text
python validar.py
python auditar_tablas.py
python auditar_seguridad.py
python smoke_test.py
python -m pip check
pip-audit -r requirements-lock.txt --no-deps --disable-pip
```

La prueba de interfaz cubre las siete vistas, cambios de unidad y territorio, filtros compartidos, limpieza de selecciones incompatibles y ausencia de desplegables de datos. Se revisaron en navegador las comparaciones de ingresos en escritorio y móvil. Las tablas comparativas usan columnas Total/Mujer/Varón y las series una fila por trimestre; se retiraron casos muestrales, ponderación interna y códigos redundantes de la presentación y los CSV.

La comparación por sexo incorpora un Total calculado con el ponderador correspondiente sobre ambos sexos del mismo período y territorio, incluso al filtrar un sexo. Se verificaron adicionalmente seis combinaciones de sexo y región mediante recálculo independiente. No se promedian las medias de los sexos. La base de precios se muestra junto a cada gráfico y tabla de ingresos: diciembre de 2025; también se identifica en los CSV.

## Comprobación específica de real frente a nominal

Se volvió a descargar el XLS oficial del IPC; su SHA-256 coincide con el conservado. Se recalcularon desde los TXT los 40 puntos de las cinco ramas mostradas en ocho trimestres. Todos coinciden con ingreso nominal ponderado multiplicado por IPC diciembre de 2025 / IPC medio del trimestre. No se encontró una serie nominal rotulada como real ni un ajuste duplicado.

Ejemplo, industria manufacturera: 1T2024, nominal $376.061 y real a diciembre de 2025 $790.531; 4T2025, nominal $1.303.247 y real $1.338.401. El factor del 4T2025 es 1,026974, no 1, porque se utiliza el IPC medio del trimestre y no el índice de diciembre como denominador. Se mantiene la aproximación trimestral documentada, con la limitación del mes de referencia de los ingresos.
