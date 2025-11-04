from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count  # ← IMPORTACIÓN AGREGADA
from .models import Cuartel, SeguimientoCuartel
from .forms import CuartelForm, SeguimientoCuartelForm

@login_required
def lista_cuarteles(request):
    cuarteles = Cuartel.objects.all().order_by('numero')
    
    # Filtros
    tipo_riego = request.GET.get('tipo_riego')
    estado = request.GET.get('estado')
    
    if tipo_riego:
        cuarteles = cuarteles.filter(tipo_riego=tipo_riego)
    if estado:
        cuarteles = cuarteles.filter(estado_cultivo=estado)
    
    # Estadísticas
    total_cuarteles = Cuartel.objects.count()
    cuarteles_activos = Cuartel.objects.filter(estado_cultivo='activo').count()
    
    context = {
        'cuarteles': cuarteles,
        'total_cuarteles': total_cuarteles,
        'cuarteles_activos': cuarteles_activos,
        'filtro_tipo_riego': tipo_riego,
        'filtro_estado': estado,
    }
    return render(request, 'cuarteles/lista_cuarteles.html', context)

@login_required
def detalle_cuartel(request, cuartel_id):
    cuartel = get_object_or_404(Cuartel, id=cuartel_id)
    seguimientos = cuartel.seguimientos.all().order_by('-fecha_seguimiento')[:10]
    
    # Form para nuevo seguimiento
    if request.method == 'POST':
        form_seguimiento = SeguimientoCuartelForm(request.POST)
        if form_seguimiento.is_valid():
            seguimiento = form_seguimiento.save(commit=False)
            seguimiento.cuartel = cuartel
            seguimiento.responsable = request.user
            seguimiento.save()
            
            # Actualizar conteo principal del cuartel
            cuartel.actualizar_conteo_plantas(
                seguimiento.plantas_vivas_registro,
                seguimiento.plantas_muertas_registro
            )
            
            messages.success(request, 'Seguimiento registrado exitosamente.')
            return redirect('cuarteles:detalle_cuartel', cuartel_id=cuartel.id)
    else:
        form_seguimiento = SeguimientoCuartelForm()
    
    context = {
        'cuartel': cuartel,
        'seguimientos': seguimientos,
        'form_seguimiento': form_seguimiento,
    }
    return render(request, 'cuarteles/detalle_cuartel.html', context)

@login_required
def crear_cuartel(request):
    if request.method == 'POST':
        form = CuartelForm(request.POST)
        if form.is_valid():
            cuartel = form.save(commit=False)
            cuartel.creado_por = request.user
            cuartel.save()
            messages.success(request, f'Cuartel {cuartel.numero} creado exitosamente.')
            return redirect('cuarteles:detalle_cuartel', cuartel_id=cuartel.id)
    else:
        form = CuartelForm()
    
    context = {'form': form}
    return render(request, 'cuarteles/crear_cuartel.html', context)

@login_required
def editar_cuartel(request, cuartel_id):
    cuartel = get_object_or_404(Cuartel, id=cuartel_id)
    
    if request.method == 'POST':
        form = CuartelForm(request.POST, instance=cuartel)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cuartel {cuartel.numero} actualizado exitosamente.')
            return redirect('cuarteles:lista_cuarteles')
    else:
        form = CuartelForm(instance=cuartel)
    
    context = {'form': form, 'cuartel': cuartel}
    return render(request, 'cuarteles/editar_cuartel.html', context)

@login_required
def eliminar_cuartel(request, cuartel_id):
    cuartel = get_object_or_404(Cuartel, id=cuartel_id)
    
    if request.method == 'POST':
        numero = cuartel.numero
        cuartel.delete()
        messages.success(request, f'Cuartel {numero} eliminado exitosamente.')
        return redirect('lista_cuarteles')
    
    context = {'cuartel': cuartel}
    return render(request, 'cuarteles/eliminar_cuartel.html', context)

@login_required
def dashboard_cuarteles(request):
    # Estadísticas para el dashboard
    total_cuarteles = Cuartel.objects.count()
    cuarteles_activos = Cuartel.objects.filter(estado_cultivo='activo').count()
    
    # Distribución por tipo de riego - CORREGIDO
    riego_stats = Cuartel.objects.values('tipo_riego').annotate(total=Count('id'))
    
    # Cuarteles con baja supervivencia (< 80%)
    baja_supervivencia = []
    for cuartel in Cuartel.objects.all():
        if cuartel.porcentaje_supervivencia() < 80:
            baja_supervivencia.append(cuartel)
    
    context = {
        'total_cuarteles': total_cuarteles,
        'cuarteles_activos': cuarteles_activos,
        'riego_stats': riego_stats,
        'baja_supervivencia': baja_supervivencia,
    }
    return render(request, 'cuarteles/dashboard.html', context)

# API para estadísticas (opcional) - CORREGIDO
@login_required
def api_estadisticas_cuarteles(request):
    data = {
        'total': Cuartel.objects.count(),
        'activos': Cuartel.objects.filter(estado_cultivo='activo').count(),
        'por_tipo_riego': list(Cuartel.objects.values('tipo_riego').annotate(total=Count('id'))),
    }
    return JsonResponse(data)