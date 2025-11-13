# inventario/models.py

from django.db import models
from autenticacion.models import Usuario as User
from django.core.exceptions import ValidationError
from django.utils.html import format_html, escape # <--- ✨ IMPORTAR 'escape' ✨

# ... (Todo el modelo Producto ... SIN CAMBIOS) ...
class Producto(models.Model):
    TIPO_CHOICES = [
        ('herbicida', 'Herbicida'),
        ('fungicida', 'Fungicida'),
        ('insecticida', 'Insecticida'),
        ('fertilizante', 'Fertilizante'),
        ('otro', 'Otro'),
    ]
    PELIGROSIDAD_CHOICES = [
        ('alto', 'Alto'),
        ('medio', 'Medio'),
        ('bajo', 'Bajo'),
    ]
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Producto')
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, verbose_name='Tipo/Categoría')
    nivel_peligrosidad = models.CharField(
        max_length=20,
        choices=PELIGROSIDAD_CHOICES,
        default='medio',
        verbose_name='Nivel de Peligrosidad'
    )
    stock_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Stock Actual'
    )
    stock_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Stock Mínimo'
    )
    unidad_medida = models.CharField(max_length=50, default='lt', verbose_name='Unidad de Medida')
    proveedor = models.CharField(max_length=200, blank=True, null=True, verbose_name='Proveedor')
    numero_registro = models.CharField(max_length=100, blank=True, null=True, verbose_name='Número de Registro')
    ingrediente_activo = models.CharField(max_length=200, blank=True, null=True, verbose_name='Ingrediente Activo')
    concentracion = models.CharField(max_length=100, blank=True, null=True, verbose_name='Concentración')
    instrucciones_uso = models.TextField(blank=True, null=True, verbose_name='Instrucciones de Uso')
    precauciones = models.TextField(blank=True, null=True, verbose_name='Precauciones de Seguridad')
    esta_activo = models.BooleanField(default=True, verbose_name='Producto Activo')
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Creado por')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')
    
    class Meta:
        db_table = 'productos'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"
    
    @property
    def estado_stock(self):
        if self.stock_actual == 0:
            return 'agotado'
        elif self.stock_actual < self.stock_minimo:
            return 'bajo'
        return 'normal'
    
    @property
    def en_alerta_stock(self):
        return self.estado_stock in ['bajo', 'agotado']

# ... (Inicio del modelo MovimientoInventario ... SIN CAMBIOS) ...
class MovimientoInventario(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    ]
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        verbose_name='Tipo de Movimiento'
    )
    fecha_movimiento = models.DateTimeField(verbose_name='Fecha del Movimiento')
    motivo = models.CharField(max_length=200, verbose_name='Motivo del Movimiento')
    referencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Referencia (Factura, Orden, etc.)'
    )
    aplicacion = models.ForeignKey(
        'aplicaciones.AplicacionFitosanitaria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
        verbose_name='Aplicación Relacionada'
    )
    realizado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Realizado por'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')
    
    class Meta:
        db_table = 'movimientos_inventario'
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha_movimiento']
    
    def __str__(self):
        return f"MOV-{self.id}: {self.get_tipo_movimiento_display()} - {self.motivo}"
    
    def clean(self):
        pass

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    # --- Métodos Helper ---
    def get_primer_detalle(self):
        return self.detalles.first()

    def get_total_detalles(self):
        return self.detalles.count()
    
    def get_productos_display(self):
        detalles = self.detalles.all()
        count = detalles.count()
        if count == 0:
            return "Sin productos"
        primer_detalle = detalles.first()
        display = f"{primer_detalle.producto.nombre}"
        if count > 1:
            display += f" (+{count - 1})"
        return display

    # --- ✨ INICIO DE LA CORRECCIÓN DEL TOOLTIP ✨ ---
    def get_detalles_display_html(self):
        """
        (CORREGIDO) Genera el HTML para el tooltip (hover)
        Usamos 'escape()' para evitar que caracteres especiales rompan el HTML.
        """
        detalles = self.detalles.all().select_related('producto')
        if not detalles:
            return "Sin detalles"
            
        html_items = [] # Construir como lista por seguridad
        for detalle in detalles:
            # Formatear la cantidad (positivo/negativo)
            cantidad_str = ""
            if self.tipo_movimiento == 'entrada':
                cantidad_str = f"+{detalle.cantidad:.2f}"
            elif self.tipo_movimiento == 'salida':
                cantidad_str = f"{-detalle.cantidad:.2f}"
            else: # Ajuste
                cantidad_str = f"{detalle.cantidad:.2f}"
            
            # Usar escape() en todas las variables de texto
            producto_nombre = escape(detalle.producto.nombre)
            unidad_medida = escape(detalle.producto.unidad_medida)

            html_items.append(
                f"<li>"
                f"<strong>{producto_nombre}:</strong> "
                f"{detalle.stock_anterior:.2f} &rarr; {detalle.stock_posterior:.2f} "
                f"({cantidad_str} {unidad_medida})"
                f"</li>"
            )
        
        # Unir la lista al final
        html_content = "".join(html_items)
        html = f'<ul class="list-unstyled mb-0 text-start">{html_content}</ul>'
        
        # format_html le dice a Django que esta cadena es segura
        return format_html(html)
    # --- ✨ FIN DE LA CORRECCIÓN DEL TOOLTIP ✨ ---


# ... (Todo el modelo DetalleMovimiento ... SIN CAMBIOS) ...
class DetalleMovimiento(models.Model):
    movimiento = models.ForeignKey(
        MovimientoInventario,
        related_name='detalles',
        on_delete=models.CASCADE
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='detalles_movimiento'
    )
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad'
    )
    stock_anterior = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Stock Anterior'
    )
    stock_posterior = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Stock Posterior'
    )
    class Meta:
        db_table = 'detalles_movimiento'
        verbose_name = 'Detalle de Movimiento'
        verbose_name_plural = 'Detalles de Movimiento'
        ordering = ['producto__nombre']
        unique_together = ('movimiento', 'producto')
    def __str__(self):
        return f"Detalle de {self.producto.nombre} para Mov. {self.movimiento.id}"


# ... (Todo el modelo EquipoAgricola ... SIN CAMBIOS) ...
class EquipoAgricola(models.Model):
    TIPO_EQUIPO_CHOICES = [
        ('maquinaria', 'Maquinaria Pesada (Tractor, etc.)'),
        ('herramienta_mayor', 'Herramienta Mayor (Escalera, etc.)'),
        ('herramienta_manual', 'Herramienta Manual (Tijeras, etc.)'),
        ('vehiculo', 'Vehículo (Camioneta, etc.)'),
        ('otro', 'Otro'),
    ]
    ESTADO_CHOICES = [
        ('operativo', 'Operativo'),
        ('mantenimiento', 'En Mantenimiento'),
        ('de_baja', 'De Baja'),
    ]
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Equipo')
    tipo = models.CharField(max_length=100, choices=TIPO_EQUIPO_CHOICES, verbose_name='Tipo de Equipo')
    modelo = models.CharField(max_length=100, blank=True, null=True, verbose_name='Modelo')
    numero_serie = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name='Número de Serie o Identificador Único',
        unique=True
    )
    fecha_compra = models.DateField(blank=True, null=True, verbose_name='Fecha de Compra')
    estado = models.CharField(
        max_length=50, 
        choices=ESTADO_CHOICES, 
        default='operativo', 
        verbose_name='Estado'
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    stock_actual = models.PositiveIntegerField(
        default=1, 
        verbose_name='Stock Actual'
    )
    stock_minimo = models.PositiveIntegerField(
        default=1, 
        verbose_name='Stock Mínimo de Alerta'
    )
    creado_en = models.DateTimeField(
        verbose_name='Creado en', 
        auto_now_add=True, 
        editable=False
    )
    class Meta:
        db_table = 'equipos_agricolas'
        verbose_name = 'Equipo Agrícola'
        verbose_name_plural = 'Equipos Agrícolas'
        ordering = ['nombre']
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"
    
    @property
    def estado_stock(self):
        if self.stock_actual == 0:
            return 'agotado'
        elif self.stock_actual < self.stock_minimo:
            return 'bajo'
        return 'normal'

    @property
    def en_alerta_stock(self):
        return self.estado_stock in ['bajo', 'agotado']