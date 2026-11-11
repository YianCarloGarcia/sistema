from django.urls import path
from . import views, views_progreso, views_masivo
from django.conf import settings
from django.contrib.staticfiles.urls import static

urlpatterns = [
    # Páginas principales
    path('', views.inicio, name='inicio'),
    path('nosotros/', views.nosotros, name='nosotros'),

    # Estudiantes
    path('estudiantes/', views.estudiantes, name='estudiantes'),
    path('estudiantes/crear/', views.crear, name='crear'),
    path('eliminar/<int:id>/', views.eliminar, name='eliminar'),
    path('estudiantes/editar/<int:id>', views.editar, name='editar'),
    path('estudiantes/detalle/<int:id>/', views.detalle, name='detalle'),

    # Historial individual (cuenta de estudiante)
    path('mi-historial/', views.mi_historial, name='mi_historial'),
    path('cambiar-clave/', views.cambiar_clave_obligatorio, name='cambiar_clave_obligatorio'),
    path('mi-progreso/', views_progreso.mi_progreso, name='mi_progreso'),
    path('mi-proceso/', views_progreso.mi_proceso, name='mi_proceso'),
    path('actividad-linea/', views_progreso.actividad_linea, name='actividad_linea'),
    path('planilla/', views.planilla_grupo, name='planilla'),
    path('notas/', views.notas_grupo, name='notas'),
    path('planilla/exportar/', views.exportar_planilla, name='exportar_planilla'),
    path('planilla/historial/', views.historial_planilla, name='historial_planilla'),

    # Escáner general (Almuerzo, Tardanzas, Uniforme, Asistencia)
    path('estudiantes/escaner/', views.escaner, name='escaner'),
    path('estudiantes/almuerzo/', views.almuerzo, name='almuerzo'),  # alias antiguo
    path('estudiantes/escaner/registrar/', views.escaner_registrar, name='escaner_registrar'),

    # Gestión masiva
    path('estudiantes/gestion-masiva/', views.gestion_masiva, name='gestion_masiva'),
    path('estudiantes/gestion-masiva/exportar/', views.exportar_estudiantes, name='exportar_estudiantes'),
    path('estudiantes/gestion-masiva/importar/', views.importar_estudiantes, name='importar_estudiantes'),
    path('estudiantes/gestion-masiva/editar-masivo/', views.editar_masivo, name='editar_masivo'),

    # Sesión
    path('logout/', views.exit, name='exit'),

    # Gestión de usuarios (solo Directivos)
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/masivo/', views_masivo.usuarios_masivo, name='usuarios_masivo'),
    path('usuarios/masivo/pendientes/', views_masivo.contar_pendientes, name='masivo_pendientes'),
    path('usuarios/masivo/estudiantes/', views_masivo.crear_estudiantes_lote, name='masivo_estudiantes'),
    path('usuarios/masivo/docentes/', views_masivo.crear_docentes_archivo, name='masivo_docentes'),
    path('usuarios/masivo/plantilla-docentes/', views_masivo.plantilla_docentes, name='plantilla_docentes'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:id>/', views.eliminar_usuario, name='eliminar_usuario'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
