from django.db import models
from django.conf import settings 
from inventario.models import EquipoAgricola
from autenticacion.models import Usuario

# ===============================================================
#  MODELO PRINCIPAL: MANTENIMIENTO (MODIFICADO)
# ===============================================================
class Mantenimiento(models.Model):
    """
    Modelo para registrar mantenimientos y calibraciones de maquinaria.
    """

    TIPO_CHOICES = [
        ('PREVENTIVA', 'Preventiva'),
        ('CORRECTIVA', 'Correctiva'),
        ('CALIBRACION', 'Calibración'),
    ]

    ESTADO_CHOICES = [
        ('PROGRAMADO', 'Programado'),
        ('REALIZADO', 'Realizado'),
        ('CANCELADO', 'Cancelado'),
    ]

    # --- Campos del Modelo ---

    maquinaria = models.ForeignKey(
        EquipoAgricola,
        on_delete=models.PROTECT, 
        related_name='mantenimientos',
        verbose_name='Maquinaria o Equipo'
    )
    
    # --- ¡NUEVO CAMPO! ---
    # Para manejar "2 de 10 tijeras"
    cantidad = models.PositiveIntegerField(
        default=1,
        verbose_name='Cantidad en Mantenimiento'
    )
    # --- FIN DE CAMPO NUEVO ---

    operario_responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL, 
        null=True,
        blank=True, 
        related_name='mantenimientos_asignados',
        verbose_name='Operario Responsable'
    )

    fecha_mantenimiento = models.DateTimeField(
        verbose_name='Fecha Programada'
    )

    descripcion_trabajo = models.TextField(
        verbose_name='Descripción del Trabajo',
        help_text='Detalle de las tareas a realizar o realizadas.'
    )

    tipo_mantenimiento = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de Mantenimiento'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PROGRAMADO', 
        verbose_name='Estado'
    )

    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mantenimientos_creados',
        verbose_name='Registrado por'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Registro'
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Actualización'
    )

    class Meta:
        db_table = 'mantenimientos'
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'
        ordering = ['-fecha_mantenimiento']

    def __str__(self):
        return f"Mantención de {self.maquinaria.nombre} - {self.fecha_mantenimiento.strftime('%d/%m/%Y')}"