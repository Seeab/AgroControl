from django.db import models
from django.utils import timezone

# Importar modelos de autenticacion
class ControlRiego(models.Model):
    """Modelo para el registro de actividades de riego - RF014, RF015, RF016, RF017"""
    
    # RF014: Horarios de inicio y término por sector
    cuartel_id = models.IntegerField(verbose_name='Sector/Cuartel')
    fecha = models.DateField(default=timezone.now)
    horario_inicio = models.TimeField(verbose_name='Horario de Inicio')
    horario_fin = models.TimeField(verbose_name='Horario de Término')
    duracion_minutos = models.IntegerField(editable=False, null=True, blank=True)
    
    # RF015: Cantidad de m³/h y m³ totales
    caudal_m3h = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Caudal (m³/h)'
    )
    volumen_total_m3 = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Volumen Total (m³)',
        editable=False,
        null=True,
        blank=True
    )
    
    # RF016: Indicar si el riego incluye fertilizante
    incluye_fertilizante = models.BooleanField(
        default=False,
        verbose_name='¿Incluye Fertilizante?'
    )
    
    # Encargado
    encargado_riego_id = models.IntegerField(null=True, blank=True)
    
    observaciones = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    creado_por = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'control_riego'
        verbose_name = 'Control de Riego'
        verbose_name_plural = 'Controles de Riego'
        ordering = ['-fecha', '-horario_inicio']

    def __str__(self):
        return f"Riego Sector {self.cuartel_id} - {self.fecha}"

    def save(self, *args, **kwargs):
        # Calcular duración en minutos
        if self.horario_inicio and self.horario_fin:
            inicio = timezone.datetime.combine(timezone.now().date(), self.horario_inicio)
            fin = timezone.datetime.combine(timezone.now().date(), self.horario_fin)
            
            if fin < inicio:
                fin += timezone.timedelta(days=1)
            
            duracion = fin - inicio
            self.duracion_minutos = int(duracion.total_seconds() / 60)
            
            # Calcular volumen total: caudal (m³/h) * duración (h)
            duracion_horas = self.duracion_minutos / 60
            self.volumen_total_m3 = self.caudal_m3h * duracion_horas
        
        super().save(*args, **kwargs)

    def get_duracion_display(self):
        """Retorna la duración en formato legible"""
        if self.duracion_minutos:
            horas = self.duracion_minutos // 60
            minutos = self.duracion_minutos % 60
            if horas > 0:
                return f"{horas}h {minutos}min"
            return f"{minutos}min"
        return "No calculado"


class FertilizanteRiego(models.Model):
    """RF017: Registrar producto y cantidad en KG cuando se usa fertilizante"""
    control_riego = models.ForeignKey(
        ControlRiego,
        on_delete=models.CASCADE,
        related_name='fertilizantes'
    )
    producto = models.CharField(max_length=200, verbose_name='Producto')
    cantidad_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad (KG)'
    )

    class Meta:
        db_table = 'fertilizantes_riego'
        verbose_name = 'Fertilizante en Riego'
        verbose_name_plural = 'Fertilizantes en Riego'

    def __str__(self):
        return f"{self.producto} - {self.cantidad_kg} kg"