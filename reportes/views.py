from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
import pandas as pd
from weasyprint import HTML
from django.template.loader import render_to_string
from django.db.models import Sum

# Decorador de login
from autenticacion.views import login_required

# Modelos que consultaremos
from riego.models import ControlRiego
from aplicaciones.models import AplicacionFitosanitaria, AplicacionProducto
from mantenimiento.models import Mantenimiento
from cuarteles.models import Cuartel
from inventario.models import Producto, EquipoAgricola

# ===============================================================
#  1. VISTA DEL FORMULARIO (HUB DE REPORTES)
#     ¡ESTA ES LA FUNCIÓN QUE TE FALTABA!
# ===============================================================
@login_required 
def pagina_reportes(request):
    """
    Muestra la página principal con el formulario para 
    seleccionar el tipo de reporte, fechas y formato.
    """
    context = {
        'cuarteles': Cuartel.objects.all().order_by('nombre'),
        'tipos_producto': Producto.TIPO_CHOICES, 
        'tipos_equipo': EquipoAgricola.TIPO_EQUIPO_CHOICES, 
        'titulo': 'Generación de Reportes'
    }
    return render(request, 'reportes/pagina_reportes.html', context)


# ===============================================================
#  2. VISTA GENERADORA (LA QUE PROCESA EL FORM)
# ===============================================================
@login_required
def generar_reporte(request):
    """
    Recibe el POST del formulario y llama a la función de 
    generación de reporte correspondiente.
    """
    if request.method != 'POST':
        return redirect('reportes:pagina_reportes')

    # --- Datos Comunes ---
    tipo_reporte = request.POST.get('tipo_reporte')
    formato = request.POST.get('formato')
    fecha_inicio_str = request.POST.get('fecha_inicio')
    fecha_fin_str = request.POST.get('fecha_fin')

    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except (ValueError, TypeError):
        messages.error(request, "Formato de fecha inválido. Use AAAA-MM-DD.")
        return redirect('reportes:pagina_reportes')

    # --- Despachador de Reportes ---
    
    # --- REPORTE DE RIEGO ---
    if tipo_reporte == 'riego':
        if formato == 'excel':
            return _generar_reporte_riego_excel(request, fecha_inicio, fecha_fin)
        elif formato == 'pdf':
            return _generar_reporte_riego_pdf(request, fecha_inicio, fecha_fin)

    # --- REPORTE DE APLICACIONES ---
    elif tipo_reporte == 'aplicacion':
        cuartel_id = request.POST.get('filtro_cuartel')
        tipo_producto = request.POST.get('filtro_tipo_producto')
        
        if formato == 'excel':
            return _generar_reporte_aplicaciones_excel(request, fecha_inicio, fecha_fin, cuartel_id, tipo_producto)
        elif formato == 'pdf':
            return _generar_reporte_aplicaciones_pdf(request, fecha_inicio, fecha_fin, cuartel_id, tipo_producto)

    # --- REPORTE DE MANTENIMIENTO ---
    elif tipo_reporte == 'mantenimiento':
        tipo_equipo = request.POST.get('filtro_tipo_equipo')
        
        if formato == 'excel':
            return _generar_reporte_mantenimiento_excel(request, fecha_inicio, fecha_fin, tipo_equipo)
        elif formato == 'pdf':
            return _generar_reporte_mantenimiento_pdf(request, fecha_inicio, fecha_fin, tipo_equipo)
    
    else:
        # messages.error(request, "Tipo de reporte no válido.") (Necesitas importar messages si usas esto)
        return redirect('reportes:pagina_reportes')

# ===============================================================
#  3. FUNCIONES AUXILIARES (LAS QUE CREAN LOS ARCHIVOS)
# ===============================================================

# --- REPORTE DE RIEGO ---

def _generar_reporte_riego_excel(request, fecha_inicio, fecha_fin):
    riegos = ControlRiego.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin],
        estado='REALIZADO'
    ).select_related('cuartel', 'encargado_riego').prefetch_related('fertilizantes__producto').order_by('fecha')
    
    data = []
    for riego in riegos:
        fecha_str = riego.fecha.strftime('%d/%m/%Y') if riego.fecha else ""
        
        if riego.incluye_fertilizante:
            lista_fert = [f"{f.producto.nombre} ({f.cantidad_kg} kg)" for f in riego.fertilizantes.all()]
            fert_str = ", ".join(lista_fert)
        else:
            fert_str = "No aplica"

        data.append({
            'Fecha': fecha_str,
            'Cuartel': riego.cuartel.nombre,
            'Hora Inicio': riego.horario_inicio,
            'Hora Fin': riego.horario_fin,
            'Duración': str(riego.get_duracion_display()),
            'Caudal (m³/h)': riego.caudal_m3h,
            'Volumen Total (m³)': riego.volumen_total_m3,
            'Fertilizantes': fert_str,
            'Encargado': str(riego.encargado_riego) if riego.encargado_riego else "N/A",
        })
    
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_riego_{fecha_inicio.date()}.xlsx"'
    df.to_excel(response, index=False, sheet_name='Riegos')
    return response

def _generar_reporte_riego_pdf(request, fecha_inicio, fecha_fin):
    riegos = ControlRiego.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin],
        estado='REALIZADO'
    ).select_related('cuartel', 'encargado_riego').prefetch_related('fertilizantes__producto').order_by('fecha')
    
    total_agua = riegos.aggregate(Sum('volumen_total_m3'))['volumen_total_m3__sum'] or 0
    
    context = {
        'riegos': riegos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_agua': total_agua,
        'fecha_generacion': timezone.now()
    }
    html_string = render_to_string('reportes/pdf_template_riego.html', context)
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_riego.pdf"'
    return response


# --- REPORTE DE APLICACIONES ---

def _generar_reporte_aplicaciones_excel(request, fecha_inicio, fecha_fin, cuartel_id, tipo_producto):
    aplicaciones = AplicacionProducto.objects.filter(
        aplicacion__fecha_aplicacion__range=[fecha_inicio, fecha_fin],
        aplicacion__estado='realizada'
    ).select_related('aplicacion', 'producto', 'aplicacion__aplicador').order_by('aplicacion__fecha_aplicacion')

    if cuartel_id: 
        aplicaciones = aplicaciones.filter(aplicacion__cuarteles__id=cuartel_id)
    if tipo_producto:
        aplicaciones = aplicaciones.filter(producto__tipo=tipo_producto)
    aplicaciones = aplicaciones.distinct()

    data = []
    for item in aplicaciones:
        fecha_str = ""
        if item.aplicacion.fecha_aplicacion:
            # Convertir a naive datetime para Excel
            fecha_naive = item.aplicacion.fecha_aplicacion.replace(tzinfo=None)
            fecha_str = fecha_naive.strftime('%d/%m/%Y %H:%M')

        data.append({
            'ID Aplicación': item.aplicacion.id,
            'Fecha': fecha_str,
            'Producto': item.producto.nombre,
            'Tipo': item.producto.get_tipo_display(),
            'Cantidad Utilizada': item.cantidad_utilizada,
            'Unidad': item.producto.unidad_medida,
            'Dosis/Ha': item.dosis_por_hectarea,
            'Cuarteles': ", ".join([c.nombre for c in item.aplicacion.cuarteles.all()]),
            'Aplicador': str(item.aplicacion.aplicador) if item.aplicacion.aplicador else "N/A",
        })
    
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_aplicaciones.xlsx"'
    df.to_excel(response, index=False, sheet_name='Aplicaciones')
    return response

def _generar_reporte_aplicaciones_pdf(request, fecha_inicio, fecha_fin, cuartel_id, tipo_producto):
    aplicaciones = AplicacionProducto.objects.filter(
        aplicacion__fecha_aplicacion__range=[fecha_inicio, fecha_fin],
        aplicacion__estado='realizada'
    ).select_related('aplicacion', 'producto').order_by('aplicacion__fecha_aplicacion')

    titulo_reporte = "Reporte de Productos Aplicados"
    if cuartel_id: 
        aplicaciones = aplicaciones.filter(aplicacion__cuarteles__id=cuartel_id)
        try:
            titulo_reporte = f"Reporte de Aplicaciones en {Cuartel.objects.get(id=cuartel_id).nombre}"
        except Cuartel.DoesNotExist: pass
    if tipo_producto:
        aplicaciones = aplicaciones.filter(producto__tipo=tipo_producto)
        titulo_reporte = f"Reporte de {tipo_producto.capitalize()}s Aplicados"
    
    aplicaciones = aplicaciones.distinct()
    
    context = {
        'aplicaciones': aplicaciones, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin,
        'titulo_reporte': titulo_reporte, 'fecha_generacion': timezone.now(),
        'totales': aplicaciones.values('producto__unidad_medida').annotate(total=Sum('cantidad_utilizada')).order_by('producto__unidad_medida')
    }
    html_string = render_to_string('reportes/pdf_template_aplicaciones.html', context)
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_aplicaciones.pdf"'
    return response


# --- REPORTE DE MANTENIMIENTO ---

def _generar_reporte_mantenimiento_excel(request, fecha_inicio, fecha_fin, tipo_equipo):
    mantenimientos = Mantenimiento.objects.filter(
        fecha_mantenimiento__range=[fecha_inicio, fecha_fin]
    ).select_related('maquinaria', 'operario_responsable').order_by('fecha_mantenimiento')
    
    if tipo_equipo:
        mantenimientos = mantenimientos.filter(maquinaria__tipo=tipo_equipo)
    
    data = []
    for mant in mantenimientos:
        fecha_str = ""
        if mant.fecha_mantenimiento:
            fecha_naive = mant.fecha_mantenimiento.replace(tzinfo=None)
            fecha_str = fecha_naive.strftime('%d/%m/%Y %H:%M')

        data.append({
            'ID': mant.id,
            'Fecha Programada': fecha_str,
            'Equipo': mant.maquinaria.nombre,
            'Categoría Equipo': mant.maquinaria.get_tipo_display(),
            'Cantidad': mant.cantidad,
            'Tipo Tarea': mant.get_tipo_mantenimiento_display(),
            'Estado': mant.get_estado_display(),
            'Responsable': str(mant.operario_responsable) if mant.operario_responsable else "N/A",
            'Descripción': mant.descripcion_trabajo,
        })
    
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_mantenimiento.xlsx"'
    df.to_excel(response, index=False, sheet_name='Mantenimientos')
    return response

def _generar_reporte_mantenimiento_pdf(request, fecha_inicio, fecha_fin, tipo_equipo):
    mantenimientos = Mantenimiento.objects.filter(
        fecha_mantenimiento__range=[fecha_inicio, fecha_fin]
    ).select_related('maquinaria', 'operario_responsable').order_by('fecha_mantenimiento')
    
    titulo_reporte = "Reporte de Mantenimiento"
    if tipo_equipo:
        mantenimientos = mantenimientos.filter(maquinaria__tipo=tipo_equipo)
        titulo_reporte = f"Reporte de Mantenimiento ({dict(EquipoAgricola.TIPO_EQUIPO_CHOICES).get(tipo_equipo)})"

    context = {
        'mantenimientos': mantenimientos, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin,
        'titulo_reporte': titulo_reporte, 'fecha_generacion': timezone.now(),
    }
    html_string = render_to_string('reportes/pdf_template_mantenimiento.html', context)
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_mantenimiento.pdf"'
    return response