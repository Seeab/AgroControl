from django import forms
from .models import Mantenimiento
from inventario.models import EquipoAgricola
from autenticacion.models import Usuario

class MantenimientoForm(forms.ModelForm):
    """
    Formulario principal (MODIFICADO con 'cantidad')
    """

    class Meta:
        model = Mantenimiento
        fields = [
            'maquinaria',
            'cantidad', # <-- ¡NUEVO!
            'tipo_mantenimiento',
            'fecha_mantenimiento',
            'operario_responsable',
            'descripcion_trabajo',
        ]
        widgets = {
            'maquinaria': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}), # <-- ¡NUEVO!
            'tipo_mantenimiento': forms.Select(attrs={'class': 'form-select'}),
            'fecha_mantenimiento': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'operario_responsable': forms.Select(attrs={'class': 'form-select'}),
            'descripcion_trabajo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'maquinaria': 'Maquinaria o Equipo',
            'cantidad': 'Cantidad a Mantener', # <-- ¡NUEVO!
            'tipo_mantenimiento': 'Tipo de Tarea',
            'fecha_mantenimiento': 'Fecha y Hora Programada',
            'operario_responsable': 'Responsable Asignado',
            'descripcion_trabajo': 'Descripción del Trabajo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Lógica de <optgroup> (SIN CAMBIOS)
        equipos_operativos = EquipoAgricola.objects.filter(estado='operativo')
        if self.instance and self.instance.pk:
            equipos_actuales = EquipoAgricola.objects.filter(pk=self.instance.maquinaria.pk)
            equipos_para_mostrar = (equipos_operativos | equipos_actuales).distinct().order_by('nombre')
        else:
            equipos_para_mostrar = equipos_operativos.order_by('nombre')
        
        grouped_choices = []
        for tipo_key, tipo_display in EquipoAgricola.TIPO_EQUIPO_CHOICES:
            equipos_en_grupo = equipos_para_mostrar.filter(tipo=tipo_key)
            if equipos_en_grupo.exists():
                lista_opciones = [
                    (equipo.id, f"{equipo.nombre} (Stock: {equipo.stock_actual})") for equipo in equipos_en_grupo
                ]
                grouped_choices.append((tipo_display, lista_opciones))

        self.fields['maquinaria'].choices = [('', 'Seleccione un equipo')] + grouped_choices

        # Lógica de Operario (SIN CAMBIOS)
        try:
            self.fields['operario_responsable'].queryset = Usuario.objects.filter(
                esta_activo=True,
                rol__nombre__in=['encargado de mantencion'] 
            ).order_by('nombres')
        except Exception:
            self.fields['operario_responsable'].queryset = Usuario.objects.filter(
                esta_activo=True
            ).order_by('nombres')
        self.fields['operario_responsable'].empty_label = "Seleccione un responsable"
        # ... (resto de la lógica del operario)

        if hasattr(Usuario, 'get_full_name') and callable(getattr(Usuario, 'get_full_name')):
             self.fields['operario_responsable'].label_from_instance = lambda obj: obj.get_full_name()
        elif hasattr(Usuario, 'nombres'):
             self.fields['operario_responsable'].label_from_instance = lambda obj: f"{obj.nombres} {obj.apellidos}"