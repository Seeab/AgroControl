from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST 

from .models import Mantenimiento
from autenticacion.models import Usuario 
from inventario.models import EquipoAgricola
from .forms import MantenimientoForm

# ... (decorador login_required) ...
def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login') 
        return view_func(request, *args, **kwargs)
    return wrapper

# ... (dashboard_mantencion sin cambios) ...
@login_required
def dashboard_mantencion(request):
    # ... (tu vista de dashboard que filtra por tipo de equipo y estado) ...
    tipo_equipo_filtro = request.GET.get('tipo_equipo', '')
    estado_filtro = request.GET.get('estado', '')
    
    mantenimientos_list = Mantenimiento.objects.select_related(
        'maquinaria', 'operario_responsable'
    ).order_by('-fecha_mantenimiento')
    
    if tipo_equipo_filtro:
        mantenimientos_list = mantenimientos_list.filter(maquinaria__tipo=tipo_equipo_filtro) 
    if estado_filtro:
        mantenimientos_list = mantenimientos_list.filter(estado=estado_filtro)
    
    total_mantenciones = mantenimientos_list.count()
    mantenciones_programadas = mantenimientos_list.filter(estado='PROGRAMADO').count()
    mantenciones_realizadas = mantenimientos_list.filter(estado='REALIZADO').count()
    
    context = {
        'total_mantenciones': total_mantenciones,
        'mantenciones_programadas': mantenciones_programadas,
        'mantenciones_realizadas': mantenciones_realizadas,
        'mantenimientos_list': mantenimientos_list, 
        'tipo_equipo_choices': EquipoAgricola.TIPO_EQUIPO_CHOICES,
        'tipo_equipo_filtro': tipo_equipo_filtro,
        'estado_filtro': estado_filtro, 
        'titulo': 'Dashboard - Mantenimiento',
        'usuario_nombre': request.session.get('usuario_nombre', 'Usuario')
    }
    return render(request, 'mantenimiento/dashboard_mantencion.html', context)


# ===============================================================
#  VISTAS CRUD (LÓGICA DE STOCK MODIFICADA)
# ===============================================================

@login_required
def crear_mantenimiento(request):
    """
    Crea una nueva mantención.
    Resta la 'cantidad' del 'stock_actual' del equipo.
    Si el stock llega a 0, también cambia el estado del equipo.
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
                    
                    # --- NUEVA LÓGICA DE STOCK ---
                    equipo = mantenimiento.maquinaria
                    cantidad = mantenimiento.cantidad
                    
                    # 1. Validar stock (seguridad)
                    if cantidad > equipo.stock_actual:
                        raise ValidationError(f'Stock insuficiente para "{equipo.nombre}". Stock operativo: {equipo.stock_actual}, se solicitan: {cantidad}.')
                    
                    # 2. Restar del stock "operativo"
                    equipo.stock_actual -= cantidad
                    
                    # 3. Si el stock operativo llega a 0, cambiar el estado del equipo
                    if equipo.stock_actual == 0:
                        equipo.estado = 'mantenimiento'
                    
                    equipo.save(update_fields=['stock_actual', 'estado'])
                    
                    # 4. Guardar la mantención
                    mantenimiento.save() 
                
                messages.success(request, f'Mantención para {cantidad}x "{equipo.nombre}" programada. Stock operativo restante: {equipo.stock_actual}.')
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
    Debe ajustar el stock si la cantidad o el equipo cambian.
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    if mantenimiento.estado != 'PROGRAMADO':
        messages.error(request, f'Esta mantención no se puede editar (estado: {mantenimiento.get_estado_display()}).')
        return redirect('mantenimiento:dashboard')

    # Guardamos los valores originales
    equipo_original = mantenimiento.maquinaria
    cantidad_original = mantenimiento.cantidad

    if request.method == 'POST':
        form = MantenimientoForm(request.POST, instance=mantenimiento)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Devolver el stock original (temporalmente)
                    equipo_original.stock_actual += cantidad_original
                    if equipo_original.stock_actual > 0:
                        equipo_original.estado = 'operativo'
                    equipo_original.save(update_fields=['stock_actual', 'estado'])

                    # 2. Obtener nuevos valores del form
                    mantenimiento_editado = form.save(commit=False)
                    equipo_nuevo = mantenimiento_editado.maquinaria
                    cantidad_nueva = mantenimiento_editado.cantidad
                    
                    # 3. Validar y restar el nuevo stock
                    # (Necesitamos refrescar el objeto si es el mismo)
                    if equipo_nuevo.id == equipo_original.id:
                        equipo_nuevo.refresh_from_db() 

                    if cantidad_nueva > equipo_nuevo.stock_actual:
                        raise ValidationError(f'Stock insuficiente para "{equipo_nuevo.nombre}". Stock operativo: {equipo_nuevo.stock_actual}, se solicitan: {cantidad_nueva}.')

                    equipo_nuevo.stock_actual -= cantidad_nueva
                    if equipo_nuevo.stock_actual == 0:
                        equipo_nuevo.estado = 'mantenimiento'
                    equipo_nuevo.save(update_fields=['stock_actual', 'estado'])
                    
                    # 4. Guardar la mantención editada
                    mantenimiento_editado.save()

                messages.success(request, 'Mantención actualizada exitosamente.')
                return redirect('mantenimiento:dashboard')
                
            except (ValidationError, Exception) as e:
                # Si falla, revertir el stock original (la transacción lo hace)
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
    # ... (Esta vista no cambia) ...
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
#  VISTAS DE ACCIÓN (LÓGICA DE STOCK MODIFICADA)
# ===============================================================

@login_required
@require_POST 
def finalizar_mantenimiento(request, pk):
    """
    Cambia el estado de 'PROGRAMADO' a 'REALIZADO'
    y DEVUELVE la 'cantidad' al 'stock_actual' del equipo.
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    if mantenimiento.estado != 'PROGRAMADO':
        messages.warning(request, f'La Tarea ID {mantenimiento.id} no se puede finalizar.')
        return redirect('mantenimiento:dashboard')

    try:
        with transaction.atomic():
            mantenimiento.estado = 'REALIZADO'
            
            # --- NUEVA LÓGICA DE STOCK ---
            equipo = mantenimiento.maquinaria
            equipo.stock_actual += mantenimiento.cantidad
            equipo.estado = 'operativo' # Al finalizar, siempre vuelve a operativo
            
            equipo.save(update_fields=['stock_actual', 'estado'])
            mantenimiento.save(update_fields=['estado'])
        
        messages.success(request, f'Mantención ID {mantenimiento.id} finalizada. {mantenimiento.cantidad}x "{equipo.nombre}" devuelto/s al stock operativo.')
    
    except Exception as e:
        messages.error(request, f'Error al finalizar Tarea ID {mantenimiento.id}: {str(e)}')
    
    return redirect('mantenimiento:dashboard')


@login_required
@require_POST 
def cancelar_mantenimiento(request, pk):
    """
    Cambia el estado de 'PROGRAMADO' a 'CANCELADO'
    y DEVUELVE la 'cantidad' al 'stock_actual' del equipo.
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    if mantenimiento.estado != 'PROGRAMADO':
        messages.warning(f'Esta tarea ya no se puede cancelar.', 'warning')
        return redirect('mantenimiento:dashboard')

    try:
        with transaction.atomic():
            mantenimiento.estado = 'CANCELADO'

            # --- NUEVA LÓGICA DE STOCK ---
            equipo = mantenimiento.maquinaria
            equipo.stock_actual += mantenimiento.cantidad
            equipo.estado = 'operativo' # Al cancelar, vuelve a operativo
            
            equipo.save(update_fields=['stock_actual', 'estado'])
            mantenimiento.save(update_fields=['estado'])
            
        messages.success(request, f'Mantención ID {mantenimiento.id} cancelada. {mantenimiento.cantidad}x "{equipo.nombre}" devuelto/s al stock operativo.')
            
        return redirect('mantenimiento:dashboard')
    
    except Exception as e:
        messages.error(request, f'Error al cancelar: {str(e)}')
        return redirect('mantenimiento:dashboard')