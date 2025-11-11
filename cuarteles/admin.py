from django.contrib import admin
from .models import Cuartel, Hilera, SeguimientoCuartel, RegistroHilera
from autenticacion.models import Usuario # Asegúrate de importar tu modelo Usuario

class HileraInline(admin.TabularInline):
    model = Hilera
    extra = 1
    fields = ('numero_hilera', 'plantas_totales_iniciales', 'plantas_vivas_actuales', 'plantas_muertas_actuales')
    readonly_fields = ('plantas_vivas_actuales', 'plantas_muertas_actuales')

# === CORREGIDO (para arreglar SystemCheckError) ===
class RegistroHileraInline(admin.TabularInline):
    model = RegistroHilera
    extra = 0
    # Usamos los nombres de campos correctos
    fields = ('hilera', 'plantas_vivas_registradas', 'plantas_muertas_registradas', 'observaciones_hilera')
    readonly_fields = ('hilera', 'plantas_vivas_registradas', 'plantas_muertas_registradas', 'observaciones_hilera')
    can_delete = False

@admin.register(Cuartel)
class CuartelAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 
        'nombre', 
        'variedad', 
        'año_plantacion', 
        'cantidad_hileras',
        'get_plantas_vivas_display',
        'get_porcentaje_supervivencia_display'
    ]
    list_filter = ['tipo_riego', 'estado_cultivo', 'año_plantacion', 'creado_por']
    search_fields = ['numero', 'nombre', 'variedad', 'ubicacion']
    readonly_fields = [
        'fecha_creacion', 'fecha_actualizacion', 
        'get_total_plantas_display', 'get_plantas_vivas_display', 
        'get_plantas_muertas_display', 'get_porcentaje_supervivencia_display'
    ]
    fieldsets = (
        ('Información Básica', {'fields': ('numero', 'nombre', 'ubicacion')}),
        ('Información del Cultivo', {'fields': ('variedad', 'tipo_planta', 'año_plantacion', 'area_hectareas')}),
        ('Estructura del Cuartel', {'fields': ('cantidad_hileras',)}),
        ('Sistema de Riego y Estado', {'fields': ('tipo_riego', 'estado_cultivo')}),
        ('Resumen de Plantas (Calculado)', {'fields': ('get_total_plantas_display', 'get_plantas_vivas_display', 'get_plantas_muertas_display', 'get_porcentaje_supervivencia_display')}),
        ('Observaciones y Auditoría', {'fields': ('observaciones', 'creado_por', 'fecha_creacion', 'fecha_actualizacion')}),
    )
    inlines = [HileraInline]

    # Métodos de display
    def get_total_plantas_display(self, obj):
        return obj.get_total_plantas()
    get_total_plantas_display.short_description = 'Total Plantas (Calculado)'

    def get_plantas_vivas_display(self, obj):
        return obj.get_plantas_vivas()
    get_plantas_vivas_display.short_description = 'Plantas Vivas (Actual)'
    
    def get_plantas_muertas_display(self, obj):
        return obj.get_plantas_muertas()
    get_plantas_muertas_display.short_description = 'Plantas Muertas (Actual)'

    def get_porcentaje_supervivencia_display(self, obj):
        return f"{obj.get_porcentaje_supervivencia():.1f}%"
    get_porcentaje_supervivencia_display.short_description = 'Supervivencia (Actual)'

    def save_model(self, request, obj, form, change):
        if not obj.creado_por_id:
            usuario_id = request.session.get('usuario_id')
            if usuario_id:
                try:
                    obj.creado_por = Usuario.objects.get(id=usuario_id)
                except Usuario.DoesNotExist:
                    pass
        super().save_model(request, obj, form, change)

@admin.register(SeguimientoCuartel)
class SeguimientoCuartelAdmin(admin.ModelAdmin):
    list_display = ['cuartel', 'fecha_seguimiento', 'responsable', 'fecha_creacion']
    list_filter = ['fecha_seguimiento', 'responsable']
    search_fields = ['cuartel__numero', 'cuartel__nombre']
    date_hierarchy = 'fecha_seguimiento'
    inlines = [RegistroHileraInline]

    def save_model(self, request, obj, form, change):
        if not obj.responsable_id:
            usuario_id = request.session.get('usuario_id')
            if usuario_id:
                try:
                    obj.responsable = Usuario.objects.get(id=usuario_id)
                except Usuario.DoesNotExist:
                    pass
        super().save_model(request, obj, form, change)