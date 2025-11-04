from django.db import models
<<<<<<< HEAD
from django.contrib.auth.models import User
from inventario.models import Producto
from cuarteles.models import Cuartel # ¡Importante! Asume que este modelo existe
from django.utils import timezone

class AplicacionFitosanitaria(models.Model):
    """Modelo para registrar aplicaciones fitosanitarias"""
    ESTADO_CHOICES = [
        ('programada', 'Programada'),
        ('realizada', 'Realizada'),
        ('cancelada', 'Cancelada'),
    ]

    # RF018: Producto
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='aplicaciones',
        verbose_name='Producto Utilizado'
    )
    
    # Campo "Nombre del aplicador" del formulario
    aplicador = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='aplicaciones_realizadas',
        verbose_name='Aplicador'
    )
    
    # RF018: Fecha y hora
    fecha_aplicacion = models.DateTimeField(
        verbose_name='Fecha y Hora de Aplicación',
        default=timezone.now
    )
    
    # Campo "Cuarteles" del formulario (Relación Muchos a Muchos)
    cuarteles = models.ManyToManyField(
        Cuartel,
        related_name='aplicaciones',
        verbose_name='Cuarteles Tratados'
    )

    # --- CAMBIOS BASADOS EN TU SUGERENCIA ---

    # Este es AHORA el campo de entrada principal
    cantidad_utilizada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad Total Utilizada', # El usuario llenará este
        default=0
    )

    # Este AHORA es un campo calculado (se calcula en el form)
    dosis_por_hectarea = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Dosis Aplicada por Hectárea (Calculada)',
        default=0,
        null=True,  # Permitir nulo si no se puede calcular
        blank=True
    )
    
    # Este AHORA es un campo calculado (se calcula en el form)
    area_tratada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Área Total Tratada (Ha)',
        default=0,
        null=True,  # Permitir nulo
        blank=True
    )

    # --- FIN DE LOS CAMBIOS ---

    # --- Campos Adicionales (de tu estructura de DB) ---
    objetivo = models.CharField(
        max_length=200,
        blank=True, null=True,
        verbose_name='Objetivo de la Aplicación (Plaga, enfermedad, etc.)'
    )
    metodo_aplicacion = models.CharField(
        max_length=100,
        blank=True, null=True,
        verbose_name='Método de Aplicación (Ej: Foliar, al suelo)'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='realizada',
        verbose_name='Estado'
    )

    # --- Auditoría ---
    creado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='aplicaciones_creadas',
        verbose_name='Registrado por'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'aplicaciones_fitosanitarias'
        verbose_name = 'Aplicación Fitosanitaria'
        verbose_name_plural = 'Aplicaciones Fitosanitarias'
        ordering = ['-fecha_aplicacion']

    def __str__(self):
        return f"Aplicación de {self.producto.nombre} el {self.fecha_aplicacion.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        # La lógica de cálculo (dosis, area) se maneja en AplicacionForm
        # para asegurar que los datos M2M (cuarteles) sean correctos.
        super().save(*args, **kwargs)
=======

# Create your models here.
>>>>>>> 45ec01aa04e8b7c823306d24fc4db20639502916
