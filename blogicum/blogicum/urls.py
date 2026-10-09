from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from blog import views as blog_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('django.contrib.auth.urls')),
    path('pages/', include('pages.urls')),
    path('', include('blog.urls')),
    path('auth/registration/', blog_views.RegisterView.as_view(),
         name='registration'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

handler403 = 'pages.views.custom_403'
handler404 = 'pages.views.custom_404'
handler500 = 'pages.views.custom_500'