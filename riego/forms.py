# riego/forms.py - CORREGIDO
from django import forms
from .models import ControlRiego, FertilizanteRiego

class ControlRiegoForm(forms.ModelForm):
    """Formulario para ControlRiego - usa solo campos que EXISTEN"""
    
    class Meta:
        model = ControlRiego
        fields = [
            'cuartel_id',           # ⬅️ Este campo SÍ existe
            'fecha',
            'horario_inicio',       # ⬅️ Este campo SÍ existe
            'horario_fin',          # ⬅️ Este campo SÍ existe
            'caudal_m3h',
            'incluye_fertilizante',
            'encargado_riego_id',   # ⬅️ Este campo SÍ existe
            'observaciones'
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'horario_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'horario_fin': forms.TimeInput(attrs={'type': 'time'}),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'cuartel_id': 'Sector/Cuartel ID',
            'horario_inicio': 'Horario de Inicio',
            'horario_fin': 'Horario de Término',
            'caudal_m3h': 'Caudal (m³/h)',
            'incluye_fertilizante': '¿Incluye Fertilizante?',
            'encargado_riego_id': 'ID Encargado de Riego',
        }

    def clean(self):
        cleaned_data = super().clean()
        horario_inicio = cleaned_data.get('horario_inicio')
        horario_fin = cleaned_data.get('horario_fin')
        
        if horario_inicio and horario_fin and horario_fin <= horario_inicio:
            raise forms.ValidationError(
                "El horario de término debe ser posterior al horario de inicio."
            )
        
        return cleaned_data


class FertilizanteRiegoForm(forms.ModelForm):
    """Formulario para FertilizanteRiego"""
    
    class Meta:
        model = FertilizanteRiego
        fields = ['producto', 'cantidad_kg']  # ⬅️ Campos que SÍ existen
        labels = {
            'cantidad_kg': 'Cantidad (KG)'
        }