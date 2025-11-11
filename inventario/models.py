from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Producto(models.Model):
    """Modelo para productos fitosanitarios y fertilizantes"""
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
    
    # Stock
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
    
    # Información adicional
    proveedor = models.CharField(max_length=200, blank=True, null=True, verbose_name='Proveedor')
    numero_registro = models.CharField(max_length=100, blank=True, null=True, verbose_name='Número de Registro')
    ingrediente_activo = models.CharField(max_length=200, blank=True, null=True, verbose_name='Ingrediente Activo')
    concentracion = models.CharField(max_length=100, blank=True, null=True, verbose_name='Concentración')
    
    # Instrucciones y precauciones
    instrucciones_uso = models.TextField(blank=True, null=True, verbose_name='Instrucciones de Uso')
    precauciones = models.TextField(blank=True, null=True, verbose_name='Precauciones de Seguridad')
    
    # Estado
    esta_activo = models.BooleanField(default=True, verbose_name='Producto Activo')
    
    # Auditoría
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
        """RF028: Determina el estado del stock (normal, bajo, agotado)"""
        if self.stock_actual == 0:
            return 'agotado'
        elif self.stock_actual < self.stock_minimo:
            return 'bajo'
        return 'normal'
    
    @property
    def en_alerta_stock(self):
        """Verifica si el producto está en alerta de stock"""
        return self.estado_stock in ['bajo', 'agotado']


class MovimientoInventario(models.Model):
    """Modelo para registrar movimientos de inventario"""
    TIPO_MOVIMIENTO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    ]
    
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='movimientos',
        verbose_name='Producto'
    )
    
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        verbose_name='Tipo de Movimiento'
    )
    
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cantidad'
    )
    
    fecha_movimiento = models.DateTimeField(verbose_name='Fecha del Movimiento')
    
    # Stock antes y después del movimiento
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
    
    # Información del movimiento
    motivo = models.CharField(max_length=200, verbose_name='Motivo del Movimiento')
    referencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Referencia (Factura, Orden, etc.)'
    )
    
    # Relación con aplicación fitosanitaria (si aplica)
    aplicacion = models.ForeignKey(
        'aplicaciones.AplicacionFitosanitaria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
        verbose_name='Aplicación Relacionada'
    )
    
    # Auditoría
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
        return f"{self.get_tipo_movimiento_display()} - {self.producto.nombre} - {self.cantidad} {self.producto.unidad_medida}"
    
    def clean(self):
            """
            Validación ANTES de guardar (usada por los formularios).
            """
            super().clean()
            
            # Validar que la cantidad sea mayor a 0
            if self.cantidad <= 0:
                raise ValidationError({'cantidad': 'La cantidad debe ser mayor a 0'})
            
            # RF020: Validar stock disponible en caso de salida
            if self.tipo_movimiento == 'salida':
                
                # ¡Importante! Si el objeto se está editando, no queremos
                # volver a validar el stock contra sí mismo.
                # Esta validación es solo para movimientos NUEVOS.
                if not self.pk: 
                    if self.cantidad > self.producto.stock_actual:
                        raise ValidationError({
                            'cantidad': f'No hay suficiente stock. Stock disponible: {self.producto.stock_actual} {self.producto.unidad_medida}'
                        })

    def save(self, *args, **kwargs):
            """
            RF021: Actualizar automáticamente el stock del producto.
            Esta es la lógica central.
            """
            
            # 1. ¿Es un objeto nuevo (siendo creado)?
            is_new = not self.pk

            # 2. Si es nuevo, realizamos todos los cálculos de stock
            if is_new:
                # 2a. Validar stock (¡importante! refrescar el producto)
                # Esto es crucial para la señal, por si el objeto 'producto'
                # que recibimos está obsoleto.
                self.producto.refresh_from_db() 
                
                if self.tipo_movimiento == 'salida' and self.cantidad > self.producto.stock_actual:
                    # Si la señal intenta sacar más de lo que hay, fallamos
                    raise ValidationError(f"Stock insuficiente al momento de guardar: {self.producto.stock_actual} disponible.")
                
                # 2b. Si la validación pasa, calculamos
                self.stock_anterior = self.producto.stock_actual
                
                if self.tipo_movimiento == 'entrada':
                    nuevo_stock = self.producto.stock_actual + self.cantidad
                elif self.tipo_movimiento == 'salida':
                    nuevo_stock = self.producto.stock_actual - self.cantidad
                else:  # ajuste
                    nuevo_stock = self.cantidad
                
                self.stock_posterior = nuevo_stock
            
            # 3. Guardar el objeto MovimientoInventario en la DB
            # (Ahora SÍ tiene stock_anterior y stock_posterior)
            super().save(*args, **kwargs)

            # 4. SOLO SI era nuevo, actualizamos el stock del Producto
            if is_new:
                self.producto.stock_actual = self.stock_posterior
                self.producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])

# --- CORRECCIÓN DE INDENTACIÓN ---
# Esta clase ahora está al nivel correcto (sin indentación)
class EquipoAgricola(models.Model):
    """
    Modelo para registrar Maquinaria y Herramientas (RF026).
    Ajustado para coincidir con la base de datos existente.
    """
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
    
    # --- CAMBIO: Ajusta este campo ---
    # Lo hacemos editable para que puedas cambiarlo si quieres
    creado_en = models.DateTimeField(
        verbose_name='Creado en', 
        auto_now_add=True, # Deja que Django lo maneje al crear
        editable=False # Sigue sin ser editable, es mejor
    )

    creado_en = models.DateTimeField(verbose_name='Creado en', auto_now_add=False, editable=False, null=True, blank=True)

    class Meta:
        db_table = 'equipos_agricolas'
        verbose_name = 'Equipo Agrícola'
        verbose_name_plural = 'Equipos Agrícolas'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"
    
    @property
    def estado_stock(self):
        """Determina el estado del stock (normal, bajo, agotado)"""
        if self.stock_actual == 0:
            return 'agotado'
        elif self.stock_actual < self.stock_minimo:
            return 'bajo'
        return 'normal'

    @property
    def en_alerta_stock(self):
        """Verifica si el equipo está en alerta de stock"""
        return self.estado_stock in ['bajo', 'agotado']