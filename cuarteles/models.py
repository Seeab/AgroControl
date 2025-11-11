from django.db import models
from autenticacion.models import Usuario
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

class Cuartel(models.Model):
    TIPO_RIEGO_CHOICES = [('goteo', 'Riego por Goteo'), ('aspersion', 'Riego por Aspersión'), ('inundacion', 'Riego por Inundación'), ('microaspersion', 'Microaspersión')]
    ESTADO_CULTIVO_CHOICES = [('activo', 'Activo'), ('inactivo', 'Inactivo'), ('en_desarrollo', 'En Desarrollo'), ('cosechado', 'Cosechado')]

    numero = models.CharField(max_length=50, unique=True, verbose_name="Número único de cuartel")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del cuartel")
    ubicacion = models.TextField(verbose_name="Ubicación")
    cantidad_hileras = models.PositiveIntegerField(default=1, verbose_name="Cantidad de Hileras")
    variedad = models.CharField(max_length=100, verbose_name="Variedad de planta")
    tipo_planta = models.CharField(max_length=100, verbose_name="Tipo de planta")
    año_plantacion = models.IntegerField(verbose_name="Año de plantación")
    tipo_riego = models.CharField(max_length=20, choices=TIPO_RIEGO_CHOICES, default='goteo', verbose_name="Tipo de riego")
    estado_cultivo = models.CharField(max_length=20, choices=ESTADO_CULTIVO_CHOICES, default='activo', verbose_name="Estado del cultivo")
    area_hectareas = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Área en hectáreas")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='cuarteles_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cuartel"
        verbose_name_plural = "Cuarteles"
        ordering = ['numero']

    def __str__(self):
        return f"Cuartel {self.numero} - {self.nombre}"

    def get_total_plantas(self):
        return self.hileras.aggregate(total=Sum('plantas_totales_iniciales'))['total'] or 0

    def get_plantas_vivas(self):
        return self.hileras.aggregate(total=Sum('plantas_vivas_actuales'))['total'] or 0

    def get_plantas_muertas(self):
        return self.hileras.aggregate(total=Sum('plantas_muertas_actuales'))['total'] or 0

    def get_porcentaje_supervivencia(self):
        total = self.get_total_plantas()
        vivas = self.get_plantas_vivas()
        if total > 0:
            return (vivas / total) * 100
        return 0

class Hilera(models.Model):
    cuartel = models.ForeignKey(Cuartel, on_delete=models.CASCADE, related_name='hileras')
    numero_hilera = models.PositiveIntegerField(verbose_name="Número de Hilera")
    plantas_totales_iniciales = models.PositiveIntegerField(default=0, verbose_name="Plantas Totales (Inicial)")
    plantas_vivas_actuales = models.PositiveIntegerField(default=0, verbose_name="Plantas Vivas (Actual)")
    plantas_muertas_actuales = models.PositiveIntegerField(default=0, verbose_name="Plantas Muertas (Actual)")

    class Meta:
        verbose_name = "Hilera"
        verbose_name_plural = "Hileras"
        ordering = ['numero_hilera']
        unique_together = ('cuartel', 'numero_hilera')

    def __str__(self):
        return f"{self.cuartel} - Hilera {self.numero_hilera}"

class SeguimientoCuartel(models.Model):
    cuartel = models.ForeignKey(Cuartel, on_delete=models.CASCADE, related_name='seguimientos_batch')
    fecha_seguimiento = models.DateField(verbose_name="Fecha de seguimiento")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones del seguimiento")
    responsable = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, verbose_name="Responsable del seguimiento")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Seguimiento (Batch)"
        verbose_name_plural = "Seguimientos (Batches)"
        ordering = ['-fecha_seguimiento']

    def __str__(self):
        return f"Seguimiento {self.cuartel.numero} - {self.fecha_seguimiento}"

class RegistroHilera(models.Model):
    seguimiento_batch = models.ForeignKey(SeguimientoCuartel, on_delete=models.CASCADE, related_name='registros_hileras')
    hilera = models.ForeignKey(Hilera, on_delete=models.CASCADE, related_name='registros')
    
    # === CORRECCIÓN ===
    # Volvemos a los campos de "registro total" como querías
    plantas_vivas_registradas = models.PositiveIntegerField(verbose_name="Plantas Vivas Registradas", default=0)
    plantas_muertas_registradas = models.PositiveIntegerField(verbose_name="Plantas Muertas Registradas", default=0)
    
    observaciones_hilera = models.TextField(blank=True, verbose_name="Observaciones de la Hilera")

    class Meta:
        verbose_name = "Registro de Hilera"
        verbose_name_plural = "Registros de Hileras"
        ordering = ['hilera__numero_hilera']

# === SEÑAL CORREGIDA ===
@receiver(post_save, sender=RegistroHilera)
def actualizar_conteo_hilera(sender, instance, created, **kwargs):
    """
    Actualiza el conteo en el modelo Hilera cada vez que
    se crea un nuevo registro de seguimiento.
    """
    if created: # Solo al crear
        hilera = instance.hilera
        
        # === LÓGICA CORREGIDA ===
        # Simplemente SETEA los valores actuales de la hilera
        # a los nuevos valores que se registraron.
        hilera.plantas_vivas_actuales = instance.plantas_vivas_registradas
        hilera.plantas_muertas_actuales = instance.plantas_muertas_registradas
            
        hilera.save()