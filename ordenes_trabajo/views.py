# ordenes_trabajo/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from datetime import datetime
from functools import wraps
import logging

# --- NUEVO: Importaciones para Paginación ---
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.utils import timezone 

# Modelos de las otras apps
from aplicaciones.models import AplicacionFitosanitaria
from riego.models import ControlRiego
from mantenimiento.models import Mantenimiento
from autenticacion.models import Usuario

# ===============================================================
#  DECORADORES DE PERMISOS
# ===============================================================

def login_required(view_func):
    """Decorador para verificar que el usuario esté logueado."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login') 
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    """Decorador para verificar que el usuario sea administrador."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('es_administrador'):
            messages.error(request, 'No tienes permisos de administrador para acceder a esta página.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ===============================================================
#  VISTA PRINCIPAL - LISTADO UNIFICADO (CON PAGINACIÓN)
# ===============================================================

@login_required
@admin_required
def lista_ordenes_trabajo(request):
    """
    RF037, RF038, RF039: Muestra lista unificada y paginada.
    """
    
    ordenes_unificadas = []

    # 1. Obtener Aplicaciones
    apps = AplicacionFitosanitaria.objects.select_related('aplicador').all()
    for app in apps:
        ordenes_unificadas.append({
            'id_obj': app.id,
            'id_str': f"APL-{app.id}",
            'tipo_orden': 'Aplicación',
            'descripcion': app.get_productos_display(), 
            'fecha_tarea': app.fecha_aplicacion,
            'responsable': app.aplicador,
            'estado': app.estado.lower(), 
            'url_detalle': reverse('aplicaciones:detalle_aplicacion', args=[app.id]),
            'es_programada': app.estado == 'programada'
        })

    # 2. Obtener Riegos
    riegos = ControlRiego.objects.select_related('encargado_riego', 'cuartel').all()
    for riego in riegos:
        # Corrección de fechas naive/aware
        naive_dt = datetime.combine(riego.fecha, riego.horario_inicio)
        try:
            fecha_tarea_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except Exception:
            fecha_tarea_dt = timezone.make_aware(naive_dt)
        
        ordenes_unificadas.append({
            'id_obj': riego.id,
            'id_str': f"RIE-{riego.id}",
            'tipo_orden': 'Riego',
            'descripcion': f"Riego en {riego.cuartel.nombre}",
            'fecha_tarea': fecha_tarea_dt,
            'responsable': riego.encargado_riego,
            'estado': riego.estado.lower(), 
            'url_detalle': reverse('riego:detalle_riego', args=[riego.id]),
            'es_programada': riego.estado == 'PROGRAMADO'
        })

    # 3. Obtener Mantenimientos
    mantenimientos = Mantenimiento.objects.select_related('operario_responsable', 'maquinaria').all()
    for mant in mantenimientos:
        ordenes_unificadas.append({
            'id_obj': mant.id,
            'id_str': f"MAN-{mant.id}",
            'tipo_orden': 'Mantenimiento',
            'descripcion': f"{mant.get_tipo_mantenimiento_display()} de {mant.maquinaria.nombre}",
            'fecha_tarea': mant.fecha_mantenimiento,
            'responsable': mant.operario_responsable,
            'estado': mant.estado.lower(), 
            'url_detalle': reverse('mantenimiento:detalle_mantenimiento', args=[mant.id]),
            'es_programada': mant.estado == 'PROGRAMADO'
        })

    # --- Filtros ---
    filtro_estado = request.GET.get('estado', '')
    filtro_tipo = request.GET.get('tipo', '')

    if filtro_estado:
        ordenes_filtradas = [o for o in ordenes_unificadas if o['estado'] == filtro_estado]
    else:
        ordenes_filtradas = ordenes_unificadas

    if filtro_tipo:
        ordenes_filtradas = [o for o in ordenes_filtradas if o['tipo_orden'].lower() == filtro_tipo]

    # --- Ordenamiento ---
    try:
        ordenes_filtradas.sort(key=lambda x: x['fecha_tarea'], reverse=True)
    except Exception as e:
        logging.error(f"Error ordenando: {e}")

    # --- Estadísticas (Calculadas sobre el total filtrado o total general según prefieras) ---
    # Aquí las calculo sobre el total general para que las tarjetas no cambien al filtrar
    total_ordenes = len(ordenes_unificadas)
    total_programadas = sum(1 for o in ordenes_unificadas if o['es_programada'])
    total_realizadas = sum(1 for o in ordenes_unificadas if o['estado'] in ['realizada', 'realizado'])

    # --- LÓGICA DE PAGINACIÓN ---
    paginator = Paginator(ordenes_filtradas, 20) # 20 elementos por página
    page_number = request.GET.get('page')
    
    try:
        ordenes_paginadas = paginator.page(page_number)
    except PageNotAnInteger:
        # Si 'page' no es un entero, mostrar la primera página.
        ordenes_paginadas = paginator.page(1)
    except EmptyPage:
        # Si la página está fuera de rango, mostrar la última.
        ordenes_paginadas = paginator.page(paginator.num_pages)

    context = {
        'ordenes': ordenes_paginadas, # Pasamos el objeto página, no la lista completa
        'total_ordenes': total_ordenes,
        'total_programadas': total_programadas,
        'total_realizadas': total_realizadas,
        'filtro_estado': filtro_estado,
        'filtro_tipo': filtro_tipo,
    }
    return render(request, 'ordenes_trabajo/lista_ordenes_trabajo.html', context)


@login_required
@admin_required
def crear_orden_trabajo(request):
    """Vista Hub (Sin cambios)"""
    context = {
        'titulo': 'Generar Nueva Orden de Trabajo'
    }
    return render(request, 'ordenes_trabajo/crear_orden_trabajo.html', context)