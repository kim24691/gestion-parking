"""
URL configuration for bujumbura_parking_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # Changement dynamique de langue
    path('', include('parking_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "Administration Parking Public Bujumbura"
admin.site.site_title = "Mairie de Bujumbura - Parking"
admin.site.index_title = "Tableau de Bord Administratif"
