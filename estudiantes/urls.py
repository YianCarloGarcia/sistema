from django.urls import path
from . import views
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
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:id>/', views.eliminar_usuario, name='eliminar_usuario'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
