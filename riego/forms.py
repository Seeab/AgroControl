# riego/forms.py - CORREGIDO
from django import forms
from .models import ControlRiego, FertilizanteRiego
from cuarteles.models import Cuartel
from inventario.models import Producto

class ControlRiegoForm(forms.ModelForm):
    """Formulario para ControlRiego corregido"""
    
    class Meta:
        model = ControlRiego
        fields = [
            'cuartel_id',  # Mantener el nombre real del campo
            'fecha',
            'horario_inicio',
            'horario_fin',
            'caudal_m3h',
            'incluye_fertilizante',
            'encargado_riego_id',  # Mantener el nombre real
            'observaciones'
        ]
        widgets = {
            'cuartel_id': forms.Select(attrs={'class': 'form-select'}),  # ⬅️ AÑADIDO
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horario_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'caudal_m3h': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'incluye_fertilizante': forms.CheckboxInput(attrs={'class': 'form-check-input'}),  # ⬅️ AÑADIDO
            'encargado_riego_id': forms.Select(attrs={'class': 'form-select'}),  # ⬅️ AÑADIDO
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'cuartel_id': 'Sector/Cuartel',  # ⬅️ CAMBIADO
            'horario_inicio': 'Horario de Inicio',
            'horario_fin': 'Horario de Término',
            'caudal_m3h': 'Caudal (m³/h)',
            'incluye_fertilizante': '¿Incluye Fertilizante?',
            'encargado_riego_id': 'Encargado de Riego',  # ⬅️ CAMBIADO
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar los querysets si es necesario
        if 'cuartel_id' in self.fields:
            self.fields['cuartel_id'].queryset = Cuartel.objects.filter(activo=True)
            self.fields['cuartel_id'].empty_label = "Seleccione un cuartel"

    def clean(self):
        cleaned_data = super().clean()
        horario_inicio = cleaned_data.get('horario_inicio')
        horario_fin = cleaned_data.get('horario_fin')
        
        if horario_inicio and horario_fin and horario_fin <= horario_inicio:
            raise forms.ValidationError(
                "El horario de término debe ser posterior al horario de inicio."
            )
        
        return cleaned_data