# riego/admin.py - COMPLETO Y CORREGIDO
from django.contrib import admin
from .models import ControlRiego, FertilizanteRiego

@admin.register(ControlRiego)
class ControlRiegoAdmin(admin.ModelAdmin):
    """Admin para ControlRiego - RF014, RF015, RF016"""
    
    # Campos que SÍ existen en el modelo
    list_display = [
        'id',
        'cuartel_id', 
        'fecha', 
        'horario_inicio', 
        'horario_fin',
        'duracion_minutos',
        'caudal_m3h',
        'volumen_total_m3',
        'incluye_fertilizante',
        'encargado_riego_id',
        'creado_en'
    ]
    
    list_filter = [
        'fecha',
        'incluye_fertilizante',
        'cuartel_id'
    ]
    
    search_fields = [
        'cuartel_id',
        'observaciones'
    ]
    
    readonly_fields = [
        'duracion_minutos',
        'volumen_total_m3',
        'creado_en'
    ]
    
    fieldsets = (
        ('Información del Riego', {
            'fields': (
                'cuartel_id',
                'fecha',
                ('horario_inicio', 'horario_fin'),
                'duracion_minutos'
            )
        }),
        ('Datos Técnicos', {
            'fields': (
                'caudal_m3h',
                'volumen_total_m3',
                'incluye_fertilizante'
            )
        }),
        ('Personal', {
            'fields': (
                'encargado_riego_id',
            )
        }),
        ('Observaciones', {
            'fields': (
                'observaciones',
            )
        }),
        ('Auditoría', {
            'fields': (
                'creado_en',
                'creado_por'
            ),
            'classes': ('collapse',)
        })
    )
    
    list_per_page = 20
    
    def get_duracion_display(self, obj):
        """Método personalizado para mostrar duración en admin"""
        return obj.get_duracion_display()
    get_duracion_display.short_description = 'Duración'
    
    def get_volumen_display(self, obj):
        """Método personalizado para mostrar volumen formateado"""
        if obj.volumen_total_m3:
            return f"{obj.volumen_total_m3} m³"
        return "No calculado"
    get_volumen_display.short_description = 'Volumen Total'


@admin.register(FertilizanteRiego)
class FertilizanteRiegoAdmin(admin.ModelAdmin):
    """Admin para FertilizanteRiego - RF017"""
    
    # Campos que SÍ existen en el modelo
    list_display = [
        'id',
        'control_riego',
        'producto',
        'cantidad_kg',
        'get_fecha_riego'
    ]
    
    list_filter = [
        'producto',
        'control_riego__fecha'
    ]
    
    search_fields = [
        'producto',
        'control_riego__cuartel_id'
    ]
    
    list_select_related = ['control_riego']
    
    list_per_page = 20
    
    def get_fecha_riego(self, obj):
        """Método para mostrar fecha del riego relacionado"""
        return obj.control_riego.fecha
    get_fecha_riego.short_description = 'Fecha Riego'
    get_fecha_riego.admin_order_field = 'control_riego__fecha'
    
    def get_cantidad_display(self, obj):
        """Método personalizado para mostrar cantidad formateada"""
        return f"{obj.cantidad_kg} kg"
    get_cantidad_display.short_description = 'Cantidad'


# Si quieres mejorar más la visualización, puedes agregar esto:
class FertilizanteRiegoInline(admin.TabularInline):
    """Inline para mostrar fertilizantes dentro de ControlRiego"""
    model = FertilizanteRiego
    extra = 1
    fields = ['producto', 'cantidad_kg']
    verbose_name = 'Fertilizante'
    verbose_name_plural = 'Fertilizantes aplicados'


# Actualizar ControlRiegoAdmin para incluir el inline
ControlRiegoAdmin.inlines = [FertilizanteRiegoInline]