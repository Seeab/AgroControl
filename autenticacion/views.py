from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Avg, F, Value
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .models import Usuario, Operario, Rol
from .forms import UsuarioForm, OperarioForm, LoginForm, RecuperarPasswordForm, CambiarPasswordForm
from django.db.models import Sum, Avg, F, Value, ExpressionWrapper, FloatField
import json

# Importamos los modelos de TODAS las apps
from riego.models import ControlRiego
from aplicaciones.models import AplicacionFitosanitaria
from mantenimiento.models import Mantenimiento
from inventario.models import Producto
from cuarteles.models import Cuartel, Hilera
from .forms import PerfilForm

from inventario.models import Producto, EquipoAgricola

# ==================== AUTENTICACIÓN ====================

def login_view(request):
    """Vista de inicio de sesión"""
    
    if request.session.get('usuario_id'):
        if request.session.get('es_administrador'):
            return redirect('dashboard') 
        rol = request.session.get('usuario_rol', 'Sin rol')
        mapa_redirecciones = {
            'administrador': 'dashboard',
            'aplicador': 'aplicaciones:lista_aplicaciones',
            'regador': 'riego:dashboard', 
            'encargado de mantencion': 'mantenimiento:dashboard',
        }
        destino = mapa_redirecciones.get(rol, 'dashboard') 
        try:
            return redirect(destino)
        except Exception:
            return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data['usuario']
            usuario.actualizar_ultimo_acceso()
            
            request.session['usuario_id'] = usuario.id
            request.session['usuario_nombre'] = usuario.get_full_name()
            request.session['usuario_rol'] = usuario.rol.nombre if usuario.rol else 'Sin rol'
            request.session['es_administrador'] = usuario.es_administrador
            
            messages.success(request, f'Bienvenido, {usuario.get_full_name()}')
            
            return redirigir_por_rol(usuario)
    else:
        form = LoginForm()
    
    return render(request, 'autenticacion/login.html', {'form': form})

def redirigir_por_rol(usuario):
    """Redirige según el rol usando nombres exactos de la BD"""
    if usuario.es_administrador:
        return redirect('dashboard')
    
    if not usuario.rol:
        return redirect('dashboard')
    
    rol_nombre = usuario.rol.nombre.strip()
    
    mapa_redirecciones = {
        'administrador': 'dashboard',
        'aplicador': 'aplicaciones:lista_aplicaciones',
        'regador': 'riego:dashboard', 
        'encargado de mantencion': 'mantenimiento:dashboard',
    }
    
    destino = mapa_redirecciones.get(rol_nombre, 'dashboard')
    
    try:
        return redirect(destino)
    except Exception as e:
        fallbacks = {
            'aplicador': 'aplicaciones_proximamente',
            'regador': 'riego_proximamente', 
            'encargado de mantencion': 'mantencion_proximamente',
        }
        fallback = fallbacks.get(rol_nombre, 'dashboard')
        return redirect(fallback)
    
def logout_view(request):
    """Vista de cierre de sesión"""
    request.session.flush()
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('login')



# ==================== DECORADORES ====================

def login_required(view_func):
    """Decorador para requerir autenticación"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    """
    Decorador para requerir permisos de administrador.
    Si no es admin, redirige a la página de Acceso Denegado.
    """
    def wrapper(request, *args, **kwargs):
        # 1. Verificar si está logueado
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión.')
            return redirect('login')
        
        # 2. Verificar si es administrador
        if not request.session.get('es_administrador'):
            # CORRECCIÓN DE SEGURIDAD: Redirigir a pantalla de error
            return redirect('acceso_denegado')
            
        return view_func(request, *args, **kwargs)
    return wrapper

def role_required(allowed_roles):
    """
    Decorador genérico que permite el acceso si:
    1. El usuario es Administrador.
    2. O el usuario tiene uno de los roles permitidos en 'allowed_roles'.
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # 1. Verificar Login
            if not request.session.get('usuario_id'):
                messages.warning(request, 'Debe iniciar sesión.')
                return redirect('login')
            
            # 2. Verificar Admin (Pase libre)
            if request.session.get('es_administrador'):
                return view_func(request, *args, **kwargs)
            
            # 3. Verificar Rol Específico
            user_rol = request.session.get('usuario_rol', '').strip().lower()
            # Normalizamos la lista de permitidos a minúsculas
            allowed_roles_norm = [r.lower() for r in allowed_roles]
            
            if user_rol in allowed_roles_norm:
                return view_func(request, *args, **kwargs)
            
            # 4. Si falla todo -> Acceso Denegado
            return redirect('acceso_denegado')
            
        return wrapper
    return decorator

# --- Decoradores Específicos (Según area del usuario) ---

def admin_required(view_func):
    """Solo para Administradores"""
    return role_required([])(view_func) # Lista vacía = nadie pasa salvo el Admin (que se chequea dentro)

def aplicador_required(view_func):
    """Para Aplicadores y Administradores"""
    return role_required(['aplicador'])(view_func)

def regador_required(view_func):
    """Para Regadores y Administradores"""
    return role_required(['regador'])(view_func)

def mantencion_required(view_func):
    """Para Encargados de Mantención y Administradores"""
    return role_required(['encargado de mantencion'])(view_func)

# ==================== Vista de error de permisos ====================

@login_required
def acceso_denegado(request):
    """Muestra la página de error 403 personalizada"""
    context = {
        'titulo': 'Acceso Denegado',
        'usuario_rol': request.session.get('usuario_rol', 'Usuario')
    }
    return render(request, 'autenticacion/acceso_denegado.html', context)


@login_required
def perfil_usuario(request):
    """
    Muestra el perfil del usuario logueado.
    """
    usuario = get_object_or_404(Usuario, pk=request.session.get('usuario_id'))
    
    # Intentamos obtener el operario asociado (si existe)
    operario = None
    try:
        operario = usuario.operario
    except Operario.DoesNotExist:
        pass

    context = {
        'usuario': usuario,
        'operario': operario, # Pasamos los datos extra si es operario
        'titulo': 'Mi Perfil'
    }
    return render(request, 'autenticacion/perfil.html', context)

@login_required
def editar_perfil(request):
    usuario = get_object_or_404(Usuario, pk=request.session.get('usuario_id'))
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario_guardado = form.save()
            request.session['usuario_nombre'] = usuario_guardado.get_full_name()
            messages.success(request, 'Tus datos han sido actualizados correctamente.')
            return redirect('perfil_usuario')
    else:
        form = PerfilForm(instance=usuario)

    context = {
        'form': form,
        'usuario': usuario, # Pasamos el usuario para lógica visual si hace falta
        'titulo': 'Editar Mis Datos',
        'boton_texto': 'Guardar Cambios'
    }
    # Usamos la plantilla con el diseño que pediste
    return render(request, 'autenticacion/perfil_editar.html', context)

# ==================== DASHBOARD (COMBINADO Y ACTUALIZADO) ====================

# En autenticacion/views.py

@admin_required
def dashboard(request):
    """
    Vista principal del dashboard (COMBINADA).
    """
    
    # 1. Configurar fechas (Rango de todo el día de hoy)
    now = timezone.now()
    # Convertir a hora local si es necesario, pero para filtrar por día usamos esto:
    hoy_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hoy_fin = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    hoy_fecha = now.date() # Para campos DateField

    # --- 1. DATOS DE USUARIOS ---
    total_usuarios = Usuario.objects.filter(esta_activo=True).count()
    total_operarios = Operario.objects.filter(esta_activo=True).count()
    usuarios_recientes = Usuario.objects.order_by('-fecha_registro')[:5] 

    # --- 2. ACTIVIDADES (Corrección de filtros) ---
    
    # Riego (Usa DateField 'fecha')
    actividades_riego = ControlRiego.objects.filter(fecha=hoy_fecha).order_by('-fecha')
    
    # Aplicaciones (Usa DateTimeField 'fecha_aplicacion')
    # Usamos __range para cubrir todo el día
    actividades_apps = AplicacionFitosanitaria.objects.filter(
        fecha_aplicacion__range=(hoy_inicio, hoy_fin)
    ).order_by('-fecha_aplicacion')
    
    # Mantenimiento (Usa DateTimeField 'fecha_mantenimiento')
    actividades_mant = Mantenimiento.objects.filter(
        fecha_mantenimiento__range=(hoy_inicio, hoy_fin)
    ).order_by('-fecha_mantenimiento')


    # --- 3. MÉTRICAS DEL DÍA ---
    
    # Riego (Realizados hoy)
    riegos_realizados_hoy = ControlRiego.objects.filter(fecha=hoy_fecha, estado='REALIZADO')
    volumen_total_dia = riegos_realizados_hoy.aggregate(total=Sum('volumen_total_m3'))['total'] or 0
    caudal_promedio_dia = riegos_realizados_hoy.aggregate(avg=Avg('caudal_m3h'))['avg'] or 0.0
    
    # Conteos para el gráfico de donas (Realizados)
    apps_realizadas_hoy = AplicacionFitosanitaria.objects.filter(
        fecha_aplicacion__range=(hoy_inicio, hoy_fin), 
        estado='realizada'
    ).count()
    
    mant_realizadas_hoy = Mantenimiento.objects.filter(
        fecha_mantenimiento__range=(hoy_inicio, hoy_fin), 
        estado='REALIZADO'
    ).count()
    
    # Conteos TOTALES para el gráfico (Programados + Realizados)
    count_riego = actividades_riego.count()
    count_apps = actividades_apps.count()
    count_mant = actividades_mant.count()


    # --- 4. ALERTAS Y OTROS DATOS (Igual que antes) ---
    ahora = timezone.now()
    treinta_dias_despues = ahora.date() + timedelta(days=30)

    alertas_stock = Producto.objects.filter(esta_activo=True, stock_actual__lt=F('stock_minimo'))
    
    alertas_mantencion = Mantenimiento.objects.filter(
        estado='PROGRAMADO', 
        fecha_mantenimiento__lt=ahora
    ).order_by('fecha_mantenimiento')

    alertas_riego = ControlRiego.objects.filter(
        estado='PROGRAMADO',
        fecha__lt=hoy_fecha 
    ).order_by('fecha')
    
    alertas_aplicaciones = AplicacionFitosanitaria.objects.filter(
        estado='programada',
        fecha_aplicacion__lt=ahora
    ).order_by('fecha_aplicacion')

    alertas_certificaciones = Operario.objects.filter(
        esta_activo=True,
        fecha_vencimiento_certificacion__range=[hoy_fecha, treinta_dias_despues]
    ).order_by('fecha_vencimiento_certificacion')
    
    # Alerta Mortalidad
    cuarteles_con_conteo = Cuartel.objects.annotate(
        total_muertas=Coalesce(Sum('hileras__plantas_muertas_actuales', output_field=DecimalField()), Value(0, output_field=DecimalField())),
        total_iniciales=Coalesce(Sum('hileras__plantas_totales_iniciales', output_field=DecimalField()), Value(0, output_field=DecimalField()))
    ).filter(total_iniciales__gt=0)
    
    alertas_mortalidad = cuarteles_con_conteo.annotate(
        porcentaje_mortalidad=ExpressionWrapper(
            (F('total_muertas') * 100.0 / F('total_iniciales')),
            output_field=FloatField()
        )
    ).filter(porcentaje_mortalidad__gt=5).order_by('-porcentaje_mortalidad')


    # --- 5. DATOS PARA GRÁFICOS ---

    # Gráfico Agua (7 días)
    fechas_grafico = []
    consumo_grafico = []
    for i in range(6, -1, -1):
        fecha_iter = hoy_fecha - timedelta(days=i)
        vol = ControlRiego.objects.filter(fecha=fecha_iter, estado='REALIZADO').aggregate(total=Sum('volumen_total_m3'))['total'] or 0
        fechas_grafico.append(fecha_iter.strftime('%d/%m'))
        consumo_grafico.append(float(vol))

    # Gráfico Stock Crítico
    prods_criticos = Producto.objects.filter(esta_activo=True).order_by('stock_actual')[:5]
    stock_labels = [p.nombre for p in prods_criticos]
    stock_data = [float(p.stock_actual) for p in prods_criticos]

    # Gráfico Maquinaria
    equipos_op = EquipoAgricola.objects.filter(estado='operativo').count()
    equipos_mant = EquipoAgricola.objects.filter(estado='mantenimiento').count()
    equipos_baja = EquipoAgricola.objects.filter(estado='de_baja').count()

    # Gráfico Cuarteles
    cuartel_labels = []
    cuartel_data = []
    for c in cuarteles_con_conteo:
        cuartel_labels.append(c.nombre)
        muertas = float(c.total_muertas)
        total = float(c.total_iniciales)
        if total > 0:
            supervivencia = ((total - muertas) / total) * 100
        else:
            supervivencia = 0
        cuartel_data.append(round(supervivencia, 1))

    context = {
        'titulo': 'Dashboard Administrativo',
        'usuario_nombre': request.session.get('usuario_nombre', 'Usuario'),
        'total_usuarios': total_usuarios,
        'total_operarios': total_operarios,
        'usuarios_recientes': usuarios_recientes,
        'actividades_riego': actividades_riego,
        'actividades_apps': actividades_apps,
        'actividades_mant': actividades_mant,
        'volumen_total_dia': volumen_total_dia,
        'caudal_promedio_dia': caudal_promedio_dia,
        'apps_realizadas_hoy': apps_realizadas_hoy,
        'mant_realizadas_hoy': mant_realizadas_hoy,
        'alertas_stock': alertas_stock,
        'alertas_mantencion': alertas_mantencion,
        'alertas_riego': alertas_riego,
        'alertas_aplicaciones': alertas_aplicaciones,
        'alertas_certificaciones': alertas_certificaciones,
        'alertas_mortalidad': alertas_mortalidad,

        # Listas puras para los gráficos
        'chart_water_labels': fechas_grafico,
        'chart_water_data': consumo_grafico,
        'chart_activity_data': [count_riego, count_apps, count_mant], # TOTALES del día
        'chart_stock_labels': stock_labels,
        'chart_stock_data': stock_data,
        'chart_machinery_data': [equipos_op, equipos_mant, equipos_baja],
        'chart_cuartel_labels': cuartel_labels,
        'chart_cuartel_data': cuartel_data,
    }
    
    return render(request, 'autenticacion/dashboard.html', context)


# ==================== GESTIÓN DE USUARIOS ====================
# (Todas tus vistas de 'usuario_lista', 'usuario_crear', etc. van aquí sin cambios)

@admin_required
def usuario_lista(request):
    """Lista de usuarios con búsqueda y paginación"""
    query = request.GET.get('q', '')
    
    # Queryset base
    usuarios_qs = Usuario.objects.select_related('rol').all()
    
    # Filtro de búsqueda
    if query:
        usuarios_qs = usuarios_qs.filter(
            Q(nombre_usuario__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(correo_electronico__icontains=query)
        )
    
    # --- MÉTRICAS (NUEVO) ---
    # Calculamos esto ANTES de la paginación
    total_usuarios = usuarios_qs.count()
    usuarios_activos = usuarios_qs.filter(esta_activo=True).count()
    usuarios_inactivos = usuarios_qs.filter(esta_activo=False).count()
    
    # Orden y Paginación
    usuarios_qs = usuarios_qs.order_by('-fecha_registro')
    paginator = Paginator(usuarios_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        # Pasamos las métricas al template
        'total_usuarios': total_usuarios,
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos,
    }
    return render(request, 'autenticacion/usuario_lista.html', context)

@admin_required
def usuario_crear(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST, is_new=True)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.nombre_usuario}" creado correctamente.')
            return redirect('usuario_lista')
    else:
        form = UsuarioForm(is_new=True)
    context = { 'form': form, 'titulo': 'Crear Usuario', 'boton_texto': 'Crear Usuario' }
    return render(request, 'autenticacion/usuario_form.html', context)

@admin_required
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario, is_new=False)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.nombre_usuario}" actualizado correctamente.')
            return redirect('usuario_lista')
    else:
        form = UsuarioForm(instance=usuario, is_new=False)
    context = { 'form': form, 'usuario': usuario, 'titulo': 'Editar Usuario', 'boton_texto': 'Guardar Cambios' }
    return render(request, 'autenticacion/usuario_form.html', context)

@admin_required
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.esta_activo = False
        usuario.save()
        messages.success(request, f'Usuario "{usuario.nombre_usuario}" desactivado correctamente.')
        return redirect('usuario_lista')
    context = {'usuario': usuario}
    return render(request, 'autenticacion/usuario_confirmar_eliminar.html', context)


# ==================== GESTIÓN DE OPERARIOS ====================

@admin_required
def operario_lista(request):
    """Lista de operarios"""
    query = request.GET.get('q', '')
    
    operarios_qs = Operario.objects.select_related('usuario').all()
    
    if query:
        operarios_qs = operarios_qs.filter(
            Q(nombre_completo__icontains=query) |
            Q(cargo__icontains=query) |
            Q(rut__icontains=query)
        )
    
    # --- MÉTRICAS (NUEVO) ---
    total_operarios = operarios_qs.count()
    operarios_activos = operarios_qs.filter(esta_activo=True).count()
    
    # Contar operarios con certificaciones por vencer (RF008)
    # Esto lo hacemos sobre el total de activos, no solo los de la búsqueda actual
    operarios_por_vencer = Operario.objects.filter(
        fecha_vencimiento_certificacion__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento_certificacion__gte=timezone.now().date(),
        esta_activo=True
    ).count()

    operarios_qs = operarios_qs.order_by('-creado_en')
    paginator = Paginator(operarios_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'total_operarios': total_operarios,
        'operarios_activos': operarios_activos,
        'operarios_por_vencer': operarios_por_vencer,
    }
    return render(request, 'autenticacion/operario_lista.html', context)

@admin_required
def operario_crear(request):
    if request.method == 'POST':
        form = OperarioForm(request.POST, request.FILES)
        if form.is_valid():
            operario = form.save(commit=False)
            usuario_id = request.POST.get('usuario_id')
            if usuario_id:
                try:
                    usuario = Usuario.objects.get(id=usuario_id)
                    operario.usuario = usuario
                except Usuario.DoesNotExist:
                    pass
            operario.save()
            messages.success(request, f'Operario "{operario.nombre_completo}" creado correctamente.')
            return redirect('operario_lista')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = OperarioForm()
    
    usuarios_disponibles = Usuario.objects.filter(
        esta_activo=True
    ).exclude(
        operario__isnull=False
    )
    
    context = {
        'form': form,
        'usuarios_disponibles': usuarios_disponibles,
        'titulo': 'Crear Operario',
        'boton_texto': 'Crear Operario'
    }
    return render(request, 'autenticacion/operario_form.html', context)

@admin_required
def operario_editar(request, pk):
    """Editar operario existente"""
    operario = get_object_or_404(Operario, pk=pk)
    
    if request.method == 'POST':
        form = OperarioForm(request.POST, request.FILES, instance=operario)
        if form.is_valid():
            operario = form.save(commit=False)
            
            # Lógica para actualizar el usuario vinculado
            usuario_id = request.POST.get('usuario_id')
            if usuario_id:
                try:
                    usuario = Usuario.objects.get(id=usuario_id)
                    operario.usuario = usuario
                except Usuario.DoesNotExist:
                    pass
            elif usuario_id == "": # Si selecciona "Ninguno" (valor vacío)
                operario.usuario = None

            operario.save()
            messages.success(request, f'Operario "{operario.nombre_completo}" actualizado correctamente.')
            return redirect('operario_lista')
    else:
        form = OperarioForm(instance=operario)
    
    # --- CORRECCIÓN: Obtener usuarios disponibles ---
    # Incluimos:
    # 1. Usuarios sin operario asignado.
    # 2. Y TAMBIÉN el usuario que YA tiene asignado este operario (si tiene uno).
    if operario.usuario:
        usuarios_disponibles = Usuario.objects.filter(
            Q(operario__isnull=True) | Q(id=operario.usuario.id),
            esta_activo=True
        )
    else:
        usuarios_disponibles = Usuario.objects.filter(
            esta_activo=True
        ).exclude(
            operario__isnull=False
        )
    
    context = {
        'form': form,
        'operario': operario,
        'usuarios_disponibles': usuarios_disponibles, # ¡Ahora sí pasamos esto!
        'titulo': 'Editar Operario',
        'boton_texto': 'Guardar Cambios'
    }
    return render(request, 'autenticacion/operario_form.html', context)

@admin_required
def operario_eliminar(request, pk):
    operario = get_object_or_404(Operario, pk=pk)
    if request.method == 'POST':
        if operario.certificacion_documento:
            operario.certificacion_documento.delete(save=False)
        operario.esta_activo = False
        operario.save()
        messages.success(request, f'Operario "{operario.nombre_completo}" desactivado correctamente.')
        return redirect('operario_lista')
    context = {'operario': operario}
    return render(request, 'autenticacion/operario_confirmar_eliminar.html', context)

# ==================== RECUPERACIÓN DE CONTRASEÑA ====================

def recuperar_password(request):
    if request.method == 'POST':
        form = RecuperarPasswordForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo_electronico']
            usuario = Usuario.objects.get(correo_electronico=correo)
            token = get_random_string(64)
            request.session[f'reset_token_{token}'] = {
                'usuario_id': usuario.id,
                'expira': (timezone.now() + timedelta(hours=1)).isoformat()
            }
            reset_link = request.build_absolute_uri(f'/password/reset/{token}/')
            try:
                send_mail(
                    'Recuperación de Contraseña - AgroControl',
                    f'Hola {usuario.get_full_name()},\n\n'
                    f'Has solicitado recuperar tu contraseña.\n\n'
                    f'Haz clic en el siguiente enlace para crear una nueva contraseña:\n'
                    f'{reset_link}\n\n'
                    f'Este enlace expirará en 1 hora.\n\n'
                    f'Si no solicitaste este cambio, ignora este mensaje.\n\n'
                    f'Saludos,\nEquipo AgroControl',
                    settings.DEFAULT_FROM_EMAIL,
                    [correo],
                    fail_silently=False,
                )
                messages.success(request, 'Se ha enviado un correo con instrucciones para recuperar tu contraseña.')
            except Exception as e:
                if settings.DEBUG:
                    messages.warning(request, f'Email no configurado. Link de recuperación: {reset_link}')
                else:
                    messages.error(request, 'Error al enviar el correo. Intenta nuevamente.')
            return redirect('login')
    else:
        form = RecuperarPasswordForm()
    return render(request, 'autenticacion/recuperar_password.html', {'form': form})


def reset_password(request, token):
    token_data = request.session.get(f'reset_token_{token}')
    if not token_data:
        messages.error(request, 'El enlace de recuperación no es válido o ha expirado.')
        return redirect('login')
    
    expira = timezone.datetime.fromisoformat(token_data['expira'])
    if timezone.now() > expira:
        del request.session[f'reset_token_{token}']
        messages.error(request, 'El enlace de recuperación ha expirado.')
        return redirect('recuperar_password')
    
    usuario = get_object_or_404(Usuario, id=token_data['usuario_id'])
    
    if request.method == 'POST':
        form = CambiarPasswordForm(request.POST)
        if form.is_valid():
            usuario.set_password(form.cleaned_data['password'])
            usuario.save()
            del request.session[f'reset_token_{token}']
            messages.success(request, 'Tu contraseña ha sido actualizada correctamente. Ahora puedes iniciar sesión.')
            return redirect('login')
    else:
        form = CambiarPasswordForm()
    context = { 'form': form, 'usuario': usuario }
    return render(request, 'autenticacion/reset_password.html', context)