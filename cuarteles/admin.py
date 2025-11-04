from django.contrib import admin
from .models import Cuartel, SeguimientoCuartel

@admin.register(Cuartel)
class CuartelAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 
        'nombre', 
        'variedad', 
        'año_plantacion', 
        'tipo_riego',
        'estado_cultivo',
        'porcentaje_supervivencia_display'
    ]
    
    list_filter = [
        'tipo_riego', 
        'estado_cultivo', 
        'año_plantacion',
        'creado_por'
    ]
    
    search_fields = ['numero', 'nombre', 'variedad', 'ubicacion']
    
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion', 'porcentaje_supervivencia_display']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero', 'nombre', 'ubicacion')
        }),
        ('Información del Cultivo', {
            'fields': ('variedad', 'tipo_planta', 'año_plantacion', 'area_hectareas')
        }),
        ('Sistema de Riego y Estado', {
            'fields': ('tipo_riego', 'estado_cultivo')
        }),
        ('Seguimiento de Plantas', {
            'fields': ('total_plantas', 'plantas_vivas', 'plantas_muertas', 'porcentaje_supervivencia_display')
        }),
        ('Observaciones y Auditoría', {
            'fields': ('observaciones', 'creado_por', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )

    def porcentaje_supervivencia_display(self, obj):
        return f"{obj.porcentaje_supervivencia():.1f}%"
    porcentaje_supervivencia_display.short_description = 'Porcentaje de Supervivencia'

    # RF010: Asegurar que el número sea único
    def save_model(self, request, obj, form, change):
        if not obj.creado_por:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

@admin.register(SeguimientoCuartel)
class SeguimientoCuartelAdmin(admin.ModelAdmin):
    list_display = ['cuartel', 'fecha_seguimiento', 'plantas_vivas_registro', 'plantas_muertas_registro', 'responsable']
    list_filter = ['fecha_seguimiento', 'responsable']
    search_fields = ['cuartel__numero', 'cuartel__nombre']
    date_hierarchy = 'fecha_seguimiento'

    def save_model(self, request, obj, form, change):
        if not obj.responsable:
            obj.responsable = request.user
        super().save_model(request, obj, form, change)