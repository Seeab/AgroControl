from django.db import models
from django.conf import settings # Buena práctica para referirse al Usuario

# Importamos los modelos de las otras apps
from inventario.models import EquipoAgricola
from autenticacion.models import Usuario

# ===============================================================
#  MODELO PRINCIPAL: MANTENIMIENTO
# ===============================================================
class Mantenimiento(models.Model):
    """
    Modelo para registrar mantenimientos y calibraciones de maquinaria.
    Cumple con RF022, RF023, RF024, RF025.
    """

    # --- Opciones para RF022 y RF024 ---
    TIPO_CHOICES = [
        ('PREVENTIVA', 'Preventiva'),
        ('CORRECTIVA', 'Correctiva'),
        ('CALIBRACION', 'Calibración'),
    ]

    # --- Opciones para el flujo de trabajo (Lógica de Aplicaciones/Riego) ---
    ESTADO_CHOICES = [
        ('PROGRAMADO', 'Programado'),
        ('REALIZADO', 'Realizado'),
        ('CANCELADO', 'Cancelado'),
    ]

    # --- Campos del Modelo ---

    # RF023: Maquinaria (Vinculado a inventario.EquipoAgricola)
    maquinaria = models.ForeignKey(
        EquipoAgricola,
        on_delete=models.PROTECT, # No permite borrar un equipo si tiene mantenciones
        related_name='mantenimientos',
        verbose_name='Maquinaria o Equipo'
    )

    # RF023 y RF025: Operario/Responsable
    operario_responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL, # Si se borra el usuario, el campo queda nulo
        null=True,
        blank=True, # Puede ser asignado después
        related_name='mantenimientos_asignados',
        verbose_name='Operario Responsable'
    )

    # RF023: Fecha
    fecha_mantenimiento = models.DateTimeField(
        verbose_name='Fecha Programada'
    )

    # RF023: Descripción
    descripcion_trabajo = models.TextField(
        verbose_name='Descripción del Trabajo',
        help_text='Detalle de las tareas a realizar o realizadas.'
    )

    # RF022 y RF024: Tipo
    tipo_mantenimiento = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de Mantenimiento'
    )

    # Campo de Estado (Implícito para el flujo de trabajo)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PROGRAMADO', # Toda nueva mantención inicia como 'PROGRAMADO'
        verbose_name='Estado'
    )

    # Campos de auditoría (Buena práctica)
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
        ordering = ['-fecha_mantenimiento'] # Mostrar los más recientes primero

    def __str__(self):
        return f"Mantención de {self.maquinaria.nombre} - {self.fecha_mantenimiento.strftime('%d/%m/%Y')}"