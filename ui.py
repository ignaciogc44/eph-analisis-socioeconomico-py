"""Elementos visuales locales: iconos SVG y metadatos de presentación."""
import html

PATHS = {
    'people': '<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M17 4a3 3 0 0 1 0 6M21 21v-3a6 6 0 0 0-4-5.65"/>',
    'briefcase': '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V4h8v3M3 12a20 20 0 0 0 18 0M10 12v3h4v-3"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5M8 10.5h5"/>',
    'wallet': '<path d="M20 8V5a2 2 0 0 0-2-2L5 6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h15V8H5"/><path d="M20 11h-6v6h6M17 14h.01"/>',
    'house': '<path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-8h6v8"/>',
    'education': '<path d="m2 9 10-5 10 5-10 5L2 9ZM6 11v6c4 3 8 3 12 0v-6M22 9v7"/>',
    'chart': '<path d="M3 3v18h18M7 15l4-5 4 3 6-7M17 6h4v4"/>',
    'grid': '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    'calendar': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 11h18M7 15h3M14 15h3"/>',
    'pin': '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    'table': '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 9v12"/>',
    'shield': '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
    'building': '<path d="M4 21V8l8-5v18M12 10h8v11M2 21h20M7 9h2M7 13h2M7 17h2M15 13h2M15 17h2"/>',
}

def icon(name, css=''):
    return '<svg class="eph-icon '+html.escape(css,quote=True)+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'+PATHS.get(name,PATHS['chart'])+'</svg>'

METRICS = {
    'Actividad': ('Actividad','people','Sobre la población total'),
    'Empleo': ('Empleo','briefcase','Sobre la población total'),
    'Desocupación': ('Desocupación','search','Sobre la población activa'),
    'Sin descuento jubilatorio': ('Sin descuento jubilatorio','shield','Asalariados con respuesta válida'),
    'Ingreso laboral · asalariados con ingresos': ('Ingreso laboral medio','wallet','Asalariados · pesos de {price_base}'),
    'IPCF medio entre hogares': ('IPCF medio entre hogares','house','Pesos de {price_base}'),
    'Secundaria finalizada · 18+': ('Secundaria completa','education','Personas de 18 años o más'),
}

CHART_ICONS = {'labor_history':'chart','overview_services':'house','dwelling':'house','tenure':'house','housing':'pin','education':'education','secondary':'education','status_sex':'people','inactivity':'people','occupation':'briefcase','sectors':'building','deciles':'wallet','income_education':'education','income_history':'chart','population':'people'}

def metric_cards(values, price_base):
    cards=[]
    for label,value in values:
        title,glyph,context=METRICS.get(label,(label,'chart',''))
        cards.append('<div class="eph-metric"><div class="eph-metric-top"><span class="eph-metric-icon">'+icon(glyph)+'</span><span class="eph-metric-label">'+html.escape(title)+'</span></div><div class="eph-metric-value">'+html.escape(str(value))+'</div><div class="eph-metric-context">'+html.escape(context.format(price_base=price_base))+'</div></div>')
    return '<div class="eph-metrics eph-metrics-'+str(len(cards))+'">'+''.join(cards)+'</div>'
