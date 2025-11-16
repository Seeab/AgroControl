# riego/models.py

from django.db import models
from django.utils import timezone
from decimal import Decimal  # ⬅️ IMPORTANTE para cálculos precisos

# Importaciones de otras apps
from cuarteles.models import Cuartel
from autenticacion.models import Usuario
from inventario.models import Producto 

# -----------------------------------------------------------------
# MODELO PRINCIPAL (Cumple RF014, RF015, RF016)
# -----------------------------------------------------------------
class ControlRiego(models.Model):
    """Modelo para el registro de actividades de riego"""
    
    # --- AÑADIR ESTA SECCIÓN ---
    class EstadoRiego(models.TextChoices):
        PROGRAMADO = 'PROGRAMADO', 'Programado'
        REALIZADO  = 'REALIZADO',  'Realizado'
        CANCELADO  = 'CANCELADO',  'Cancelado'
    # ------------------------------
    # RF014: Cuartel, Horario de Inicio y Fin
    cuartel = models.ForeignKey(
        Cuartel,
        on_delete=models.CASCADE,
        verbose_name='Sector/Cuartel',
        related_name='riegos'
    )
    horario_inicio = models.TimeField(verbose_name='Horario de Inicio')
    horario_fin = models.TimeField(verbose_name='Horario de Término')

    estado = models.CharField(
        max_length=12,
        choices=EstadoRiego.choices,
        default=EstadoRiego.PROGRAMADO,  # Asumimos que si se crea es porque se realizó
        verbose_name='Estado del Riego'
    )
    
    # RF015: Caudal y Volumen
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
    
    # RF016: ¿Incluye fertilizante?
    incluye_fertilizante = models.BooleanField(
        default=False,
        verbose_name='¿Incluye Fertilizante?'
    )
    
    # --- Otros campos ---
    fecha = models.DateField(default=timezone.now)
    duracion_minutos = models.IntegerField(editable=False, null=True, blank=True)
    
    encargado_riego = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Encargado de Riego',
        related_name='riegos_asignados'
    )
    
    observaciones = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='riegos_creados'
    )

    class Meta:
        db_table = 'control_riego'
        verbose_name = 'Control de Riego'
        verbose_name_plural = 'Controles de Riego'
        ordering = ['-fecha', '-horario_inicio']

    def __str__(self):
        return f"Riego {self.cuartel.nombre} - {self.fecha}"

    def save(self, *args, **kwargs):
        # Calcular duración en minutos
        if self.horario_inicio and self.horario_fin:
            inicio = timezone.datetime.combine(timezone.now().date(), self.horario_inicio)
            fin = timezone.datetime.combine(timezone.now().date(), self.horario_fin)
            
            if fin < inicio:
                fin += timezone.timedelta(days=1)
            
            duracion = fin - inicio
            self.duracion_minutos = int(duracion.total_seconds() / 60)
            
            # Calcular volumen total (con Decimal)
            if self.caudal_m3h and self.duracion_minutos:
                duracion_horas = Decimal(self.duracion_minutos) / Decimal('60.0')
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

# -----------------------------------------------------------------
# MODELO SECUNDARIO (Cumple RF017)
# -----------------------------------------------------------------
class FertilizanteRiego(models.Model):
    """
    Registra los productos y cantidades de fertilizante
    usados en un ControlRiego específico.
    """
    
    # Relación con el riego principal
    control_riego = models.ForeignKey(
        ControlRiego,
        on_delete=models.CASCADE,
        related_name='fertilizantes'  # Permite acceder desde riego: riego.fertilizantes.all()
    )
    
    # RF017: Producto y Cantidad
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,  # Evita borrar un producto si está en un registro
        verbose_name='Producto'
    )
    cantidad_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad (kg)'
    )

    class Meta:
        db_table = 'control_riego_fertilizantes'
        verbose_name = 'Fertilizante de Riego'
        verbose_name_plural = 'Fertilizantes de Riego'
        # Evita que se añada el mismo producto dos veces en el mismo riego
        unique_together = ('control_riego', 'producto')

    def __str__(self):
        return f"{self.cantidad_kg} kg de {self.producto.nombre}"