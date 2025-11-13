# inventario/forms.py

from django import forms
from django.forms import inlineformset_factory # Importar
from .models import Producto, MovimientoInventario, DetalleMovimiento, EquipoAgricola

class ProductoForm(forms.ModelForm):
    """(SIN CAMBIOS)"""
    class Meta:
        model = Producto
        fields = [
            'nombre', 'tipo', 'nivel_peligrosidad', 'unidad_medida',
            'stock_actual', 'stock_minimo', 'proveedor', 'numero_registro',
            'ingrediente_activo', 'concentracion', 'instrucciones_uso',
            'precauciones', 'esta_activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'nivel_peligrosidad': forms.Select(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('lt', 'Litros (lt)'),
                ('kg', 'Kilogramos (kg)'),
                ('gr', 'Gramos (gr)'),
                ('ml', 'Mililitros (ml)'),
                ('un', 'Unidades (un)'),
            ]),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_registro': forms.TextInput(attrs={'class': 'form-control'}),
            'ingrediente_activo': forms.TextInput(attrs={'class': 'form-control'}),
            'concentracion': forms.TextInput(attrs={'class': 'form-control'}),
            'instrucciones_uso': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precauciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'esta_activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MovimientoInventarioForm(forms.ModelForm):
    """Formulario para el encabezado del Movimiento (MODIFICADO)"""
    class Meta:
        model = MovimientoInventario
        # --- CAMPOS MODIFICADOS ---
        # Quitamos 'producto' y 'cantidad'
        fields = ['tipo_movimiento', 'fecha_movimiento', 'motivo', 'referencia']
        widgets = {
            'tipo_movimiento': forms.Select(attrs={'class': 'form-control'}),
            'fecha_movimiento': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M' # Formato HTML5
            ),
            'motivo': forms.TextInput(attrs={'class': 'form-control'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Sobrescribimos __init__ para limitar los tipos de movimiento.
        (CORREGIDO: Se quitó la inicialización de la fecha)
        """
        super().__init__(*args, **kwargs)
        
        # ✨ INICIO DE LA CORRECCIÓN (Timezone) ✨
        # Se eliminó la línea que forzaba la hora a UTC:
        # self.fields['fecha_movimiento'].initial = forms.utils.timezone.now().strftime('%Y-%m-%dT%H:%M')
        # Ahora, el widget <input type="datetime-local"> usará la hora local del navegador.
        # ✨ FIN DE LA CORRECCIÓN ✨
        
        # No permitir crear movimientos de 'salida' manualmente
        # Las salidas solo se hacen desde 'Aplicaciones'
        self.fields['tipo_movimiento'].choices = [
            ('entrada', 'Entrada'),
            ('ajuste', 'Ajuste'),
        ]
        self.fields['tipo_movimiento'].initial = 'entrada'


class DetalleMovimientoForm(forms.ModelForm):
    """(NUEVO) Formulario para el detalle (el producto y la cantidad)"""
    
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(esta_activo=True).order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-control producto-select'})
    )
    
    cantidad = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )

    class Meta:
        model = DetalleMovimiento
        fields = ['producto', 'cantidad']

    def clean(self):
        """Validación de stock (solo para 'salida' o 'ajuste' negativo)"""
        cleaned_data = super().clean()
        
        # El tipo de movimiento está en el formulario "padre"
        # Accedemos a él a través del formset
        # (Esto es complejo, mejor validamos en la VISTA)
        
        # Mantenemos una validación simple de cantidad > 0
        if not cleaned_data.get('DELETE', False):
            cantidad = cleaned_data.get('cantidad')
            if cantidad and cantidad <= 0:
                raise forms.ValidationError("La cantidad debe ser mayor a 0.")
            if not cleaned_data.get('producto'):
                raise forms.ValidationError("Debe seleccionar un producto.")

        return cleaned_data


# --- NUEVO FORMSET ---
DetalleMovimientoFormSet = inlineformset_factory(
    MovimientoInventario,       # Modelo Padre
    DetalleMovimiento,          # Modelo Hijo
    form=DetalleMovimientoForm, # Formulario para el hijo
    extra=1,                    # Empezar con 1 formulario vacío
    can_delete=True,            # Permitir borrar
    fk_name='movimiento',
    min_num=1,                  # Exigir al menos 1 producto
    validate_min=True,
)


class EquipoAgricolaForm(forms.ModelForm):
    """(SIN CAMBIOS)"""
    class Meta:
        model = EquipoAgricola
        # --- AÑADIDO: 'stock_actual', 'stock_minimo' ---
        fields = [
            'nombre', 'tipo', 'estado', 'modelo', 'numero_serie', 
            'fecha_compra', 'stock_actual', 'stock_minimo', 'observaciones'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Tractor John Deere 5075E'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 5075E'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Identificador único'}),
            'fecha_compra': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
            # --- AÑADIDO: Widgets de Stock ---
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
        labels = {
            'nombre': 'Nombre del Equipo o Herramienta *',
            'tipo': 'Tipo *',
            'estado': 'Estado Actual *',
            'numero_serie': 'N° Serie o Identificador',
            'fecha_compra': 'Fecha de Adquisición',
            # --- AÑADIDO: Labels de Stock ---
            'stock_actual': 'Cantidad Actual (Stock) *',
            'stock_minimo': 'Stock Mínimo de Alerta *',
        }