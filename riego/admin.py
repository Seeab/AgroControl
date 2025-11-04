from django.contrib import admin
from .models import ControlRiego, FertilizanteRiego


class FertilizanteRiegoInline(admin.TabularInline):
    model = FertilizanteRiego
    extra = 1


@admin.register(ControlRiego)
class ControlRiegoAdmin(admin.ModelAdmin):
    list_display = ('cuartel_id', 'fecha', 'horario_inicio', 'horario_fin', 
                    'duracion_minutos', 'caudal_m3h', 'volumen_total_m3', 
                    'incluye_fertilizante')
    list_filter = ('incluye_fertilizante', 'fecha')
    search_fields = ('cuartel_id', 'observaciones')
    readonly_fields = ('duracion_minutos', 'volumen_total_m3', 'creado_en')
    date_hierarchy = 'fecha'
    inlines = [FertilizanteRiegoInline]
    
    fieldsets = (
        ('RF014: Sector y Horarios', {
            'fields': ('cuartel_id', 'fecha', 'horario_inicio', 'horario_fin', 'duracion_minutos')
        }),
        ('RF015: Mediciones de Agua', {
            'fields': ('caudal_m3h', 'volumen_total_m3')
        }),
        ('RF016: Fertirriego', {
            'fields': ('incluye_fertilizante',)
        }),
        ('Responsable', {
            'fields': ('encargado_riego_id',)
        }),
        ('Observaciones', {
            'fields': ('observaciones', 'creado_en', 'creado_por')
        }),
    )


@admin.register(FertilizanteRiego)
class FertilizanteRiegoAdmin(admin.ModelAdmin):
    list_display = ('control_riego', 'producto', 'cantidad_kg', 'get_fecha')
    list_filter = ('control_riego__fecha',)
    search_fields = ('producto', 'control_riego__cuartel_id')
    
    def get_fecha(self, obj):
        return obj.control_riego.fecha
    get_fecha.short_description = 'Fecha'
    get_fecha.admin_order_field = 'control_riego__fecha'