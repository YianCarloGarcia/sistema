from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Estudiante


class EstudianteForm(forms.ModelForm):
    class Meta:
        model  = Estudiante
        fields = '__all__'
        widgets = {
            'jornada':  forms.Select(attrs={'class': 'form-select'}),
            'tipo':     forms.Select(attrs={'class': 'form-select'}),
            'linea':    forms.Select(attrs={'class': 'form-select'}),
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
            'observaciones':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'foto':                forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


ROL_CHOICES = [
    ('docente',   'Docente — puede ver y buscar, no editar'),
    ('directivo', 'Directivo — acceso completo'),
]


class UsuarioCrearForm(UserCreationForm):
    """Formulario para crear usuarios con rol y correo."""
    first_name = forms.CharField(
        label='Nombres', max_length=60,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        label='Apellidos', max_length=60,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        help_text='Se enviará un correo de bienvenida con las credenciales.',
    )
    rol = forms.ChoiceField(
        label='Rol', choices=ROL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['username'].help_text = 'Solo letras, números y @/./+/-/_'


class UsuarioEditarForm(forms.ModelForm):
    """Formulario para editar usuario existente (sin cambiar contraseña aquí)."""
    rol = forms.ChoiceField(
        label='Rol', choices=ROL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
        widgets = {
            'username':   forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        # Precarga el rol desde los grupos del usuario
        instance = kwargs.get('instance')
        initial  = kwargs.get('initial', {})
        if instance:
            grupos = list(instance.groups.values_list('name', flat=True))
            if 'directivo' in grupos:
                initial['rol'] = 'directivo'
            else:
                initial['rol'] = 'docente'
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
