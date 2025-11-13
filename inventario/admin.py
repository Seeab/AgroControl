# inventario/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from .models import Producto , MovimientoInventario, EquipoAgricola

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

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = [
        'producto',
        'tipo_movimiento',
        'cantidad_display',
        'stock_anterior_display',
        'stock_posterior_display',
        'realizado_por',
        'fecha_movimiento'
    ]
    
    list_filter = ['tipo_movimiento', 'fecha_movimiento', 'producto']
    
    search_fields = ['producto__nombre', 'motivo', 'referencia']
    
    readonly_fields = ['stock_anterior', 'stock_posterior', 'fecha_registro']
    
    def cantidad_display(self, obj):
        return f"{obj.cantidad} {obj.producto.unidad_medida}"
    cantidad_display.short_description = 'Cantidad'

    def stock_anterior_display(self, obj):
        return f"{obj.stock_anterior} {obj.producto.unidad_medida}"
    stock_anterior_display.short_description = 'Stock Anterior'

    def stock_posterior_display(self, obj):
        return f"{obj.stock_posterior} {obj.producto.unidad_medida}"
    stock_posterior_display.short_description = 'Stock Posterior'

    # --- CORRECCIÓN 3: 'save_model' para 'MovimientoInventario' ---
    def save_model(self, request, obj, form, change):
        if not obj.realizado_por_id:
            try:
                usuario_custom = Usuario.objects.get(nombre_usuario=request.user.username)
                obj.realizado_por = usuario_custom
            except Usuario.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)

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