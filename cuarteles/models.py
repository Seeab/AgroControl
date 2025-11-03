from django.db import models
from django.contrib.auth.models import User

class Cuartel(models.Model):
    TIPO_RIEGO_CHOICES = [
        ('goteo', 'Riego por Goteo'),
        ('aspersion', 'Riego por Aspersión'),
        ('inundacion', 'Riego por Inundación'),
        ('microaspersion', 'Microaspersión'),
    ]
    
    ESTADO_CULTIVO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('en_desarrollo', 'En Desarrollo'),
        ('cosechado', 'Cosechado'),
    ]

    # RF010: Registro con número único y ubicación
    numero = models.CharField(max_length=50, unique=True, verbose_name="Número único de cuartel")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del cuartel")
    ubicacion = models.TextField(verbose_name="Ubicación")
    
    # RF011: Plantas y variedades específicas
    variedad = models.CharField(max_length=100, verbose_name="Variedad de planta")
    tipo_planta = models.CharField(max_length=100, verbose_name="Tipo de planta")
    
    # RF012: Año de plantación, tipo de riego y estado
    año_plantacion = models.IntegerField(verbose_name="Año de plantación")
    tipo_riego = models.CharField(
        max_length=20, 
        choices=TIPO_RIEGO_CHOICES, 
        default='goteo',
        verbose_name="Tipo de riego"
    )
    estado_cultivo = models.CharField(
        max_length=20, 
        choices=ESTADO_CULTIVO_CHOICES, 
        default='activo',
        verbose_name="Estado del cultivo"
    )
    
    # RF013: Seguimiento de plantas vivas vs muertas
    total_plantas = models.IntegerField(default=0, verbose_name="Total de plantas")
    plantas_vivas = models.IntegerField(default=0, verbose_name="Plantas vivas")
    plantas_muertas = models.IntegerField(default=0, verbose_name="Plantas muertas")
    
    # Información adicional
    area_hectareas = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Área en hectáreas"
    )
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cuarteles_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cuartel"
        verbose_name_plural = "Cuarteles"
        ordering = ['numero']

    def __str__(self):
        return f"Cuartel {self.numero} - {self.nombre}"

    # RF013: Método para calcular porcentaje de supervivencia
    def porcentaje_supervivencia(self):
        if self.total_plantas > 0:
            return (self.plantas_vivas / self.total_plantas) * 100
        return 0

    # Método para actualizar conteo de plantas
    def actualizar_conteo_plantas(self, vivas, muertas):
        self.plantas_vivas = vivas
        self.plantas_muertas = muertas
        self.total_plantas = vivas + muertas
        self.save()

class SeguimientoCuartel(models.Model):
    cuartel = models.ForeignKey(Cuartel, on_delete=models.CASCADE, related_name='seguimientos')
    fecha_seguimiento = models.DateField(verbose_name="Fecha de seguimiento")
    
    # RF013: Datos específicos del seguimiento
    plantas_vivas_registro = models.IntegerField(verbose_name="Plantas vivas en este registro")
    plantas_muertas_registro = models.IntegerField(verbose_name="Plantas muertas en este registro")
    
    observaciones = models.TextField(blank=True, verbose_name="Observaciones del seguimiento")
    responsable = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Responsable del seguimiento")
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Seguimiento de Cuartel"
        verbose_name_plural = "Seguimientos de Cuarteles"
        ordering = ['-fecha_seguimiento']

    def __str__(self):
        return f"Seguimiento {self.cuartel.numero} - {self.fecha_seguimiento}"