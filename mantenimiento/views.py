from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST # ¡Importante!


# Modelos de esta app
from .models import Mantenimiento

# Modelos de otras apps
from autenticacion.models import Usuario 
from inventario.models import EquipoAgricola

# Formularios
from .forms import MantenimientoForm

# --- Decorador de Login (SIN CAMBIOS) ---
def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login') 
        return view_func(request, *args, **kwargs)
    return wrapper

# ===============================================================
#  VISTA PRINCIPAL: dashboard_mantencion (MODIFICADA)
# ===============================================================
@login_required
def dashboard_mantencion(request):
    """
    Dashboard principal con filtros para TIPO DE EQUIPO y Estado.
    """
    
    # --- 1. LÓGICA DE FILTROS (MODIFICADA) ---
    tipo_equipo_filtro = request.GET.get('tipo_equipo', '') # <-- CAMBIO: Filtro por tipo de equipo
    estado_filtro = request.GET.get('estado', '')
    
    mantenimientos_list = Mantenimiento.objects.select_related(
        'maquinaria', 'operario_responsable'
    ).order_by('-fecha_mantenimiento')
    
    if tipo_equipo_filtro: # <-- CAMBIO
        mantenimientos_list = mantenimientos_list.filter(maquinaria__tipo=tipo_equipo_filtro)
    if estado_filtro:
        mantenimientos_list = mantenimientos_list.filter(estado=estado_filtro)
    
    # --- 2. LÓGICA DE ESTADÍSTICAS (TARJETAS) ---
    # Usamos la lista filtrada para las estadísticas principales
    total_mantenciones = mantenimientos_list.count()
    mantenciones_programadas = mantenimientos_list.filter(estado='PROGRAMADO').count()
    mantenciones_realizadas = mantenimientos_list.filter(estado='REALIZADO').count()
    
    # --- TARJETA "EQUIPOS EN MANTENCIÓN" ELIMINADA ---
    
    # --- 3. CONTEXTO PARA LA PLANTILLA ---
    context = {
        # Estadísticas (3 tarjetas)
        'total_mantenciones': total_mantenciones,
        'mantenciones_programadas': mantenciones_programadas,
        'mantenciones_realizadas': mantenciones_realizadas,
        
        # Lista (Sin paginación)
        'mantenimientos_list': mantenimientos_list, 
        
        # Datos para rellenar los filtros (MODIFICADOS)
        'tipo_equipo_choices': EquipoAgricola.TIPO_EQUIPO_CHOICES, # Pasamos los choices de EquipoAgricola
        'tipo_equipo_filtro': tipo_equipo_filtro,
        'estado_filtro': estado_filtro, 
        
        'titulo': 'Dashboard - Mantenimiento',
        'usuario_nombre': request.session.get('usuario_nombre', 'Usuario')
    }
    return render(request, 'mantenimiento/dashboard_mantencion.html', context)


# ===============================================================
#  VISTAS CRUD (Lógica de "Programar" -> "Finalizar")
# ===============================================================

@login_required
def crear_mantenimiento(request):
    """
    Crea una nueva mantención.
    Pone el equipo en estado 'mantenimiento'.
    """
    
    usuario_id = request.session.get('usuario_id')
    try:
        usuario_logueado = Usuario.objects.get(id=usuario_id)
    except (Usuario.DoesNotExist, TypeError):
        messages.error(request, 'Error de autenticación. Inicia sesión de nuevo.')
        return redirect('login')
    
    if request.method == 'POST':
        form = MantenimientoForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    mantenimiento = form.save(commit=False)
                    mantenimiento.creado_por = usuario_logueado 
                    mantenimiento.estado = 'PROGRAMADO'
                    
                    equipo = mantenimiento.maquinaria
                    
                    if equipo.estado != 'operativo':
                        raise ValidationError(f'El equipo "{equipo.nombre}" ya no está operativo (estado actual: {equipo.get_estado_display()}).')
                    
                    equipo.estado = 'mantenimiento'
                    equipo.save(update_fields=['estado'])
                    
                    mantenimiento.save() 
                
                messages.success(request, f'Mantención para "{equipo.nombre}" programada. El equipo ahora figura "En Mantenimiento".')
                return redirect('mantenimiento:dashboard')
            
            except (ValidationError, Exception) as e:
                form.add_error(None, f"Error al guardar la mantención: {str(e)}")
                messages.error(request, 'No se pudo crear la mantención. Revisa los errores.')
        
        else: 
            messages.error(request, 'Por favor corrige los errores del formulario.')

    else: # request.method == 'GET'
        form = MantenimientoForm()
    
    context = {
        'form': form,
        'titulo': 'Programar Mantenimiento',
        'boton_texto': 'Guardar'
    }
    return render(request, 'mantenimiento/mantenimiento_form.html', context)


@login_required
def editar_mantenimiento(request, pk):
    """
    Edita una mantención 'PROGRAMADA'.
    Permite cambiar la maquinaria (liberando la antigua y bloqueando la nueva).
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    if mantenimiento.estado != 'PROGRAMADO':
        messages.error(request, f'Esta mantención no se puede editar (estado: {mantenimiento.get_estado_display()}).')
        return redirect('mantenimiento:dashboard')

    id_equipo_original = mantenimiento.maquinaria.id

    if request.method == 'POST':
        form = MantenimientoForm(request.POST, instance=mantenimiento)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    mantenimiento_editado = form.save()
                    
                    id_equipo_nuevo = mantenimiento_editado.maquinaria.id
                    
                    if id_equipo_original != id_equipo_nuevo:
                        
                        equipo_original = EquipoAgricola.objects.get(id=id_equipo_original)
                        equipo_original.estado = 'operativo'
                        equipo_original.save(update_fields=['estado'])
                        
                        equipo_nuevo = mantenimiento_editado.maquinaria
                        if equipo_nuevo.estado != 'operativo':
                             raise ValidationError(f'El nuevo equipo "{equipo_nuevo.nombre}" no está operativo.')
                        
                        equipo_nuevo.estado = 'mantenimiento'
                        equipo_nuevo.save(update_fields=['estado'])

                messages.success(request, 'Mantención actualizada exitosamente.')
                return redirect('mantenimiento:dashboard')
                
            except (ValidationError, Exception) as e:
                form.add_error(None, f"Error al actualizar: {str(e)}")
                messages.error(request, 'No se pudo actualizar la mantención.')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = MantenimientoForm(instance=mantenimiento)
    
    context = {
        'form': form,
        'mantenimiento': mantenimiento,
        'titulo': 'Editar Mantenimiento',
        'boton_texto': 'Actualizar'
    }
    return render(request, 'mantenimiento/mantenimiento_form.html', context)


@login_required
def detalle_mantenimiento(request, pk):
    """Muestra el detalle de una mantención."""
    mantenimiento = get_object_or_404(
        Mantenimiento.objects.select_related(
            'maquinaria', 'operario_responsable', 'creado_por'
        ), 
        pk=pk
    )
    
    context = {
        'mantenimiento': mantenimiento,
        'titulo': f'Detalle Mantención #{mantenimiento.id}'
    }
    return render(request, 'mantenimiento/detalle_mantenimiento.html', context)


# ===============================================================
#  VISTAS DE ACCIÓN (Lógica de "Programar" -> "Finalizar")
# ===============================================================

@login_required
@require_POST 
def finalizar_mantenimiento(request, pk):
    """
    Cambia el estado de 'PROGRAMADO' a 'REALIZADO'
    y pone el equipo 'operativo'.
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    if mantenimiento.estado != 'PROGRAMADO':
        messages.warning(request, f'La Tarea ID {mantenimiento.id} no se puede finalizar.')
        return redirect('mantenimiento:dashboard')

    try:
        with transaction.atomic():
            mantenimiento.estado = 'REALIZADO'
            mantenimiento.save(update_fields=['estado'])
            
            equipo = mantenimiento.maquinaria
            equipo.estado = 'operativo'
            equipo.save(update_fields=['estado'])
        
        messages.success(request, f'Mantención ID {mantenimiento.id} finalizada. Equipo "{equipo.nombre}" está "Operativo".')
    
    except Exception as e:
        messages.error(request, f'Error al finalizar Tarea ID {mantenimiento.id}: {str(e)}')
    
    return redirect('mantenimiento:dashboard')


@login_required
@require_POST 
def cancelar_mantenimiento(request, pk):
    """
    Cambia el estado de 'PROGRAMADO' a 'CANCELADO'
    y pone el equipo 'operativo'.
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    if mantenimiento.estado != 'PROGRAMADO':
        messages.warning(f'Esta tarea ya no se puede cancelar.', 'warning')
        return redirect('mantenimiento:dashboard')

    try:
        with transaction.atomic():
            mantenimiento.estado = 'CANCELADO'
            mantenimiento.save(update_fields=['estado'])

            equipo = mantenimiento.maquinaria
            equipo.estado = 'operativo'
            equipo.save(update_fields=['estado'])
            
        messages.success(request, f'Mantención ID {mantenimiento.id} cancelada. Equipo "{equipo.nombre}" está "Operativo".')
            
        return redirect('mantenimiento:dashboard')
    
    except Exception as e:
        messages.error(request, f'Error al cancelar: {str(e)}')
        return redirect('mantenimiento:dashboard')
    
