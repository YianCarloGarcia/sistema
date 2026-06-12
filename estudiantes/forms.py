from django import forms
from .models import Estudiante


class EstudianteForm(forms.ModelForm):

    class Meta:
        model  = Estudiante
        fields = '__all__'
        widgets = {
            # Selects
            'jornada':  forms.Select(attrs={'class': 'form-select'}),
            'tipo':     forms.Select(attrs={'class': 'form-select'}),
            'linea':    forms.Select(attrs={'class': 'form-select'}),
            # Texto simple
            'documento':           forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos':           forms.TextInput(attrs={'class': 'form-control'}),
            'nombres':             forms.TextInput(attrs={'class': 'form-control'}),
            'curso':               forms.TextInput(attrs={'class': 'form-control'}),
            'celular':             forms.TextInput(attrs={'class': 'form-control'}),
            'email':               forms.EmailInput(attrs={'class': 'form-control'}),
            'acudiente':           forms.TextInput(attrs={'class': 'form-control'}),
            'parentesco':          forms.TextInput(attrs={'class': 'form-control'}),
            'tel_acudiente':       forms.TextInput(attrs={'class': 'form-control'}),
            'tel2_acudiente':      forms.TextInput(attrs={'class': 'form-control'}),
            'direccion':           forms.TextInput(attrs={'class': 'form-control'}),
            'ocupacion_acudiente': forms.TextInput(attrs={'class': 'form-control'}),
            'eps':                 forms.TextInput(attrs={'class': 'form-control'}),
            # Textarea
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # Foto
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
