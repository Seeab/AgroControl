# aplicaciones/models.py

from django.db import models
from django.db.models import Sum
from autenticacion.models import Usuario as User
from inventario.models import Producto, EquipoAgricola
from cuarteles.models import Cuartel
from django.utils import timezone

class AplicacionFitosanitaria(models.Model):
    """Modelo para registrar aplicaciones fitosanitarias (MODIFICADO)"""
    ESTADO_CHOICES = [
        ('programada', 'Programada'),
        ('realizada', 'Realizada'),
        ('cancelada', 'Cancelada'),
    ]

    # --- CAMPOS ELIMINADOS ---
    # La FK a 'producto' se ha ido.
    # 'cantidad_utilizada' se ha ido.
    # 'dosis_por_hectarea' se ha ido.
    # --- FIN CAMPOS ELIMINADOS ---

    # --- NUEVO CAMPO M2M ---
    # Esta es la nueva relación que usa la tabla intermedia 'AplicacionProducto'
    productos = models.ManyToManyField(
        Producto,
        through='AplicacionProducto',
        related_name='aplicaciones',
        verbose_name='Productos Utilizados'
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
    
    # Este AHORA es un campo calculado (se calcula en el form/save)
    area_tratada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Área Total Tratada (Ha)',
        default=0,
        null=True,
        blank=True
    )

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
        default='programada', # Cambiado a 'programada' por defecto
        verbose_name='Estado'
    )

    # --- ✨ NUEVO CAMPO AÑADIDO --- (Este ya lo tenías)
    equipo_utilizado = models.ForeignKey(
        EquipoAgricola,
        on_delete=models.SET_NULL, # Si borras el equipo, la aplicación no se borra
        null=True, 
        blank=True, 
        verbose_name='Equipo Utilizado (Opcional)',
        related_name='aplicaciones_fitosanitarias'
    )
    # --- FIN DEL NUEVO CAMPO ---

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
        # Usar 'self.get_primer_producto()' que definimos abajo
        primer_prod = self.get_primer_producto()
        nombre_prod = primer_prod.producto.nombre if primer_prod else "N/A"
        return f"Aplicación de {nombre_prod} el {self.fecha_aplicacion.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        # Calcular el área tratada total al guardar la aplicación
        if self.pk: # Solo si ya existe y tiene cuarteles
             # Usamos .all() que funciona después de que el form M2M se guarda
            area_total = self.cuarteles.all().aggregate(Sum('area_hectareas'))['area_hectareas__sum']
            self.area_tratada = area_total or 0
        super().save(*args, **kwargs)

    # --- MÉTODOS HELPER PARA TEMPLATES ---

    def get_primer_producto(self):
        """Devuelve la primera instancia de AplicacionProducto"""
        # Accedemos a la tabla intermedia a través del related_name 'aplicacionproducto_set'
        return self.aplicacionproducto_set.first()

    def get_total_productos(self):
        """Devuelve el conteo de productos distintos"""
        return self.aplicacionproducto_set.count()
    
    def get_productos_display(self):
        """Para mostrar en la lista 'Producto... +X'"""
        detalles = self.aplicacionproducto_set.all()
        count = detalles.count()
        
        if count == 0:
            return "Sin productos"
        
        primer_detalle = detalles.first()
        display = f"{primer_detalle.producto.nombre}"
        
        if count > 1:
            display += f" (+{count - 1})"
            
        return display


class AplicacionProducto(models.Model):
    """
    (NUEVO MODELO) Tabla intermedia para Aplicacion <-> Producto
    Aquí es donde se guarda la cantidad de CADA producto.
    """
    aplicacion = models.ForeignKey(
        AplicacionFitosanitaria, 
        on_delete=models.CASCADE
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.PROTECT,
        verbose_name="Producto"
    )
    cantidad_utilizada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad Total Utilizada'
    )
    # Este campo se calculará
    dosis_por_hectarea = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Dosis/Ha (Calculada)',
        default=0,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'aplicaciones_productos'
        verbose_name = 'Producto de Aplicación'
        verbose_name_plural = 'Productos de Aplicación'
        unique_together = ('aplicacion', 'producto') # No repetir el producto en la misma app

    def __str__(self):
        return f"{self.producto.nombre} ({self.cantidad_utilizada} {self.producto.unidad_medida})"
    
    def save(self, *args, **kwargs):
        # Calcular dosis/ha al guardar
        if self.aplicacion.area_tratada and self.aplicacion.area_tratada > 0:
            self.dosis_por_hectarea = self.cantidad_utilizada / self.aplicacion.area_tratada
        else:
            self.dosis_por_hectarea = 0
        super().save(*args, **kwargs)