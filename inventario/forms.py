from django import forms
from .models import Producto, MovimientoInventario, EquipoAgricola

class ProductoForm(forms.ModelForm):
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
    class Meta:
        model = MovimientoInventario
        fields = ['producto', 'tipo_movimiento', 'cantidad', 'fecha_movimiento', 'motivo', 'referencia']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'tipo_movimiento': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'fecha_movimiento': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto')
        tipo_movimiento = cleaned_data.get('tipo_movimiento')
        cantidad = cleaned_data.get('cantidad')
        
        if producto and tipo_movimiento and cantidad:
            if tipo_movimiento == 'salida' and cantidad > producto.stock_actual:
                raise forms.ValidationError(
                    f"No hay suficiente stock. Stock disponible: {producto.stock_actual} {producto.unidad_medida}"
                )
        
        return cleaned_data


class EquipoAgricolaForm(forms.ModelForm):
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