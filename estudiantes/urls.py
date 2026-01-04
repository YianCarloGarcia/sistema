from django.urls import path
from . import views
from django.conf import settings
from django.contrib.staticfiles.urls import static

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('nosotros/', views.nosotros, name='nosotros'),
    path('estudiantes/', views.estudiantes, name='estudiantes'),
    path('estudiantes/crear/', views.crear, name='crear'),
    path('estudiantes/editar/', views.editar, name='editar'),
    path('eliminar/<int:id>/', views.eliminar, name='eliminar'),
    path('estudiantes/editar/<int:id>', views.editar, name='editar'),
    path('estudiantes/detalle/<int:id>/', views.detalle, name='detalle'),
    path('estudiantes/almuerzo/', views.almuerzo, name='almuerzo'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)