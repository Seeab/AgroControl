# inventario/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.db import transaction  # <--- ✨ ¡AQUÍ ESTÁ LA CORRECCIÓN! ✨
from .models import Producto , MovimientoInventario, EquipoAgricola, DetalleMovimiento
from .forms import DetalleMovimientoForm

# --- CORRECCIÓN 1: Importar tu Usuario personalizado ---
from autenticacion.models import Usuario

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 
        'tipo', 
        'nivel_peligrosidad',
        'stock_actual_display', 
        'stock_minimo',
        'estado_stock_display',
        'esta_activo'
    ]
    
    list_filter = [
        'tipo', 
        'nivel_peligrosidad', 
        'esta_activo',
        'proveedor'
    ]
    
    search_fields = ['nombre', 'proveedor', 'ingrediente_activo']
    
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion', 'estado_stock_display']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'tipo', 'nivel_peligrosidad', 'esta_activo')
        }),
        ('Control de Stock', {
            'fields': ('stock_actual', 'stock_minimo', 'unidad_medida', 'estado_stock_display')
        }),
        ('Información Técnica', {
            'fields': ('proveedor', 'numero_registro', 'ingrediente_activo', 'concentracion')
        }),
        ('Seguridad', {
            'fields': ('instrucciones_uso', 'precauciones')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )

    def stock_actual_display(self, obj):
        return f"{obj.stock_actual} {obj.unidad_medida}"
    stock_actual_display.short_description = 'Stock Actual'

    def estado_stock_display(self, obj):
        if obj.estado_stock == 'agotado':
            return format_html('<span style="color: red; font-weight: bold;">❌ Agotado</span>')
        elif obj.estado_stock == 'bajo':
            return format_html('<span style="color: orange; font-weight: bold;">⚠️ Bajo</span>')
        else:
            return format_html('<span style="color: green; font-weight: bold;">✅ Normal</span>')
    estado_stock_display.short_description = 'Estado Stock'

    # RF028: Acción para productos con stock bajo
    def productos_stock_bajo(self, request, queryset):
        productos_bajos = queryset.filter(stock_actual__lt=models.F('stock_minimo'))
        self.message_user(
            request, 
            f"Se encontraron {productos_bajos.count()} productos con stock bajo"
        )
    productos_stock_bajo.short_description = "Ver productos con stock bajo"

    actions = [productos_stock_bajo]

    # --- CORRECCIÓN 2: 'save_model' para 'Producto' ---
    def save_model(self, request, obj, form, change):
        if not obj.creado_por_id: # Es mejor verificar el _id
            try:
                # 'request.user' es el usuario del admin de Django
                # 'usuario_custom' es tu usuario de la app 'autenticacion'
                usuario_custom = Usuario.objects.get(nombre_usuario=request.user.username)
                obj.creado_por = usuario_custom
            except Usuario.DoesNotExist:
                # Si no lo encuentra, lo deja en blanco
                pass 
        super().save_model(request, obj, form, change)


# --- NUEVO INLINE ---
class DetalleMovimientoInline(admin.TabularInline):
    model = DetalleMovimiento
    form = DetalleMovimientoForm # Usamos el form que valida cantidad > 0
    extra = 1
    # Campos que se muestran en el admin inline
    fields = ('producto', 'cantidad', 'stock_anterior', 'stock_posterior')
    # Hacemos que los stocks sean de solo lectura en el admin
    readonly_fields = ('stock_anterior', 'stock_posterior')
    autocomplete_fields = ['producto']


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    # --- CAMPOS MODIFICADOS ---
    # (Esto corrige los errores E108 y E116 de SystemCheck)
    list_display = [
        'id',
        'tipo_movimiento',
        'get_productos_display', # Helper del modelo
        'realizado_por',
        'fecha_movimiento',
        'referencia',
        'aplicacion'
    ]
    
    list_filter = ['tipo_movimiento', 'fecha_movimiento']
    
    search_fields = ['motivo', 'referencia', 'detalles__producto__nombre']
    
    # (Esto corrige los errores E035 de SystemCheck)
    readonly_fields = ['fecha_registro']
    
    # --- AÑADIR EL INLINE ---
    inlines = [DetalleMovimientoInline]
    
    # No permitir añadir/editar detalles si es una 'salida' (se maneja por la app)
    def get_inlines(self, request, obj=None):
        if obj and obj.tipo_movimiento == 'salida':
            # Clonamos el inline para modificarlo
            class DetalleMovimientoSalidaInline(DetalleMovimientoInline):
                can_delete = False
                extra = 0
                def has_add_permission(self, request, obj=None):
                    return False
                def has_change_permission(self, request, obj=None):
                    return False
            return [DetalleMovimientoSalidaInline]
        return super().get_inlines(request, obj)

    def get_queryset(self, request):
        # Optimizar la carga
        return super().get_queryset(request).prefetch_related('detalles__producto')

    # --- CORRECCIÓN 3: 'save_model' para 'MovimientoInventario' ---
    def save_model(self, request, obj, form, change):
        if not obj.realizado_por_id:
            try:
                usuario_custom = Usuario.objects.get(nombre_usuario=request.user.username)
                obj.realizado_por = usuario_custom
            except Usuario.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)
    
    @transaction.atomic # <--- Esta línea necesitaba el import
    def save_related(self, request, form, formsets, change):
        """
        Lógica de stock para el Admin (Entrada/Ajuste)
        """
        # Guardar el padre (Movimiento) primero
        super().save_related(request, form, formsets, change)
        
        movimiento = form.instance
        
        # Solo actuar en Entrada o Ajuste (Salida es automática)
        if movimiento.tipo_movimiento in ['entrada', 'ajuste']:
            
            # formsets[0] es nuestro DetalleMovimientoInline
            # Iteramos sobre los formularios guardados
            for detalle in movimiento.detalles.all():
                
                # Si el stock_anterior no está seteado, es nuevo o necesita recálculo
                if detalle.stock_anterior == 0 and detalle.stock_posterior == 0:
                    producto = detalle.producto
                    cantidad = detalle.cantidad
                    
                    producto.refresh_from_db()
                    stock_anterior = producto.stock_actual
                    
                    if movimiento.tipo_movimiento == 'entrada':
                        stock_posterior = stock_anterior + cantidad
                    else: # Ajuste
                        stock_posterior = cantidad
                    
                    detalle.stock_anterior = stock_anterior
                    detalle.stock_posterior = stock_posterior
                    detalle.save()
                    
                    producto.stock_actual = stock_posterior
                    producto.save(update_fields=['stock_actual'])


@admin.register(EquipoAgricola)
class EquipoAgricolaAdmin(admin.ModelAdmin):
    # --- AÑADIDO: 'stock_actual', 'stock_minimo' ---
    list_display = [
        'nombre', 'tipo', 'estado', 'stock_actual', 
        'stock_minimo', 'modelo', 'numero_serie', 'fecha_compra', 'creado_en'
    ]
    list_filter = ['tipo', 'estado', 'fecha_compra']
    search_fields = ['nombre', 'modelo', 'numero_serie']
    readonly_fields = ['creado_en']
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'tipo', 'estado', 'modelo', 'numero_serie')
        }),
        # --- AÑADIDO: Fieldset de Stock ---
        ('Control de Stock', {
            'fields': ('stock_actual', 'stock_minimo')
        }),
        ('Historial', {
            'fields': ('fecha_compra', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('creado_en',) 
        }),
    )
    # NOTA: Este modelo no tiene 'creado_por', así que no necesita save_model