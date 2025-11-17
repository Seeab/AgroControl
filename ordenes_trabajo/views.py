# ordenes_trabajo/views.py (CORREGIDO)
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from datetime import datetime
from functools import wraps
import logging # Para registrar errores

# Importar timezone para corregir el ordenamiento
from django.utils import timezone 

# Modelos de las otras apps que usaremos
from aplicaciones.models import AplicacionFitosanitaria
from riego.models import ControlRiego
from mantenimiento.models import Mantenimiento
from autenticacion.models import Usuario

# ===============================================================
#  DECORADORES DE PERMISOS (Sin cambios)
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
            return redirect('dashboard') # Redirige al dashboard principal
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ===============================================================
#  VISTA PRINCIPAL - LISTADO UNIFICADO (Corregido)
# ===============================================================

@login_required
@admin_required
def lista_ordenes_trabajo(request):
    """
    RF037, RF038, RF039: Muestra una lista unificada de todas las "órdenes de trabajo"
    (Aplicaciones, Riegos y Mantenimientos).
    """
    
    ordenes_unificadas = []

    # 1. Obtener Aplicaciones (Fechas "aware" - con zona horaria UTC)
    apps = AplicacionFitosanitaria.objects.select_related('aplicador').all()
    for app in apps:
        ordenes_unificadas.append({
            'id_obj': app.id,
            'id_str': f"APL-{app.id}",
            'tipo_orden': 'Aplicación',
            'descripcion': app.get_productos_display(), 
            'fecha_tarea': app.fecha_aplicacion, # Es un DateTimeField (aware)
            'responsable': app.aplicador,
            'estado': app.estado.lower(), 
            'url_detalle': reverse('aplicaciones:detalle_aplicacion', args=[app.id]),
            'es_programada': app.estado == 'programada'
        })

    # 2. Obtener Riegos (Fechas "naive" - sin zona horaria)
    riegos = ControlRiego.objects.select_related('encargado_riego', 'cuartel').all()
    for riego in riegos:
        
        # --- ¡INICIO DE LA CORRECCIÓN DE ORDENAMIENTO! ---
        # Combinamos la fecha y hora "naive" (ingenuas)
        naive_dt = datetime.combine(riego.fecha, riego.horario_inicio)
        # Convertimos la fecha "naive" en "aware" (consciente)
        # Asumimos que la hora guardada está en la zona horaria del proyecto (settings.TIME_ZONE)
        fecha_tarea_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        # --- FIN DE LA CORRECCIÓN ---
        
        ordenes_unificadas.append({
            'id_obj': riego.id,
            'id_str': f"RIE-{riego.id}",
            'tipo_orden': 'Riego',
            'descripcion': f"Riego en {riego.cuartel.nombre}",
            'fecha_tarea': fecha_tarea_dt, # <-- Ahora es "aware"
            'responsable': riego.encargado_riego,
            'estado': riego.estado.lower(), 
            'url_detalle': reverse('riego:detalle_riego', args=[riego.id]),
            'es_programada': riego.estado == 'PROGRAMADO'
        })

    # 3. Obtener Mantenimientos (Fechas "aware" - con zona horaria UTC)
    mantenimientos = Mantenimiento.objects.select_related('operario_responsable', 'maquinaria').all()
    for mant in mantenimientos:
        ordenes_unificadas.append({
            'id_obj': mant.id,
            'id_str': f"MAN-{mant.id}",
            'tipo_orden': 'Mantenimiento',
            'descripcion': f"{mant.get_tipo_mantenimiento_display()} de {mant.maquinaria.nombre}",
            'fecha_tarea': mant.fecha_mantenimiento, # Es un DateTimeField (aware)
            'responsable': mant.operario_responsable,
            'estado': mant.estado.lower(), 
            'url_detalle': reverse('mantenimiento:detalle_mantenimiento', args=[mant.id]),
            'es_programada': mant.estado == 'PROGRAMADO'
        })

    # --- Lógica de Filtros (Sin cambios) ---
    filtro_estado = request.GET.get('estado', '')
    filtro_tipo = request.GET.get('tipo', '')

    if filtro_estado:
        ordenes_filtradas = [o for o in ordenes_unificadas if o['estado'] == filtro_estado]
    else:
        ordenes_filtradas = ordenes_unificadas

    if filtro_tipo:
        ordenes_filtradas = [o for o in ordenes_filtradas if o['tipo_orden'].lower() == filtro_tipo]

    # --- Ordenamiento Corregido ---
    try:
        # Ahora que todas las fechas son "aware", el ordenamiento funcionará
        ordenes_filtradas.sort(key=lambda x: x['fecha_tarea'], reverse=True)
    except TypeError as e:
        # En caso de que algo siga fallando (ej. una fecha es None)
        logging.warning(f"Error al ordenar órdenes de trabajo: {e}")
    except Exception as e:
        logging.error(f"Error inesperado al ordenar órdenes de trabajo: {e}")

    # --- Estadísticas (Tarjetas) (Sin cambios) ---
    total_ordenes = len(ordenes_unificadas)
    total_programadas = sum(1 for o in ordenes_unificadas if o['es_programada'])
    total_realizadas = sum(1 for o in ordenes_unificadas if o['estado'] == 'realizada' or o['estado'] == 'realizado')

    context = {
        'ordenes': ordenes_filtradas,
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
    """
    RF037: Vista "Hub" que permite a los Jefes/Admins 
    seleccionar qué tipo de orden de trabajo generar.
    (Sin cambios)
    """
    context = {
        'titulo': 'Generar Nueva Orden de Trabajo'
    }
    return render(request, 'ordenes_trabajo/crear_orden_trabajo.html', context)