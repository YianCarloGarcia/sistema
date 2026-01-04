from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Estudiante
from .models import Asistencia
from .forms import EstudianteForm
from django.utils import timezone
from datetime import timedelta
from urllib.parse import quote_plus
import csv
from io import TextIOWrapper
from django.contrib import messages
# Create your views here.

def inicio(request):
    return render(request, 'paginas/inicio.html')

def nosotros(request):
    return render(request, 'paginas/nosotros.html')

def estudiantes(request):
    estudiantes = Estudiante.objects.all()
    #print(estudiantes)
    


    return render(request, 'estudiantes/index.html', {'estudiantes': estudiantes})

def crear(request):
    formulario = EstudianteForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('estudiantes')
    return render(request, 'estudiantes/crear.html', {'formulario': formulario})

def editar(request, id):
    estudiante = Estudiante.objects.get(id=id)
    formulario = EstudianteForm(request.POST or None, request.FILES or None, instance=estudiante, )
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('estudiantes')
    return render(request, 'estudiantes/editar.html', {'formulario': formulario})

def eliminar(request, id):
    estudiante = Estudiante.objects.get(id=id)
    estudiante.delete()
    return redirect('estudiantes')

def detalle(request, id):
    estudiante = Estudiante.objects.get(id=id)
    return render(request, 'estudiantes/detalle.html', {'estudiante': estudiante})

BLOQUEO_SEGUNDOS = 5

def almuerzo(request):
    mensaje = None
    contador = None
    nombre = None

    if request.method == 'POST':
        documento = request.POST.get('documento')

        try:
            estudiante = Estudiante.objects.get(documento=documento)

            ahora = timezone.now()
            limite = ahora - timedelta(seconds=BLOQUEO_SEGUNDOS)

            ultimo = Asistencia.objects.filter(estudiante = estudiante, tipo = 'ALM').order_by('-fecha', '-hora').first()


            if ultimo:
                fecha_hora_ultimo = timezone.make_aware(timezone.datetime.combine(ultimo.fecha, ultimo.hora))

                if fecha_hora_ultimo > limite:
                    mensaje = f"⏳ Espere {BLOQUEO_SEGUNDOS} segundos antes de volver a escanear"
                else:
                    Asistencia.objects.create(estudiante=estudiante, tipo='ALM')
            else:
                Asistencia.objects.create(estudiante=estudiante, tipo='ALM')

            
            
            
            hoy = timezone.localdate()
            contador = Asistencia.objects.filter(estudiante=estudiante, fecha=hoy, tipo='ALM').count()
            nombre = f"{estudiante.nombres} {estudiante.apellidos}"
            mensaje = f"Almuerzos registrados hoy: {contador}"

        except Estudiante.DoesNotExist:
            mensaje = "Documento no encontrado"

    return render(request, 'estudiantes/almuerzo.html', {'mensaje': mensaje, 'contador': contador, 'nombre': nombre})


