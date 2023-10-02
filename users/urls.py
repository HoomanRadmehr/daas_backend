from django.urls import path
from users import views
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

router = routers.SimpleRouter()
router.register("daas",views.DaasView)

app_name="users"
urlpatterns = [
    path("login/",views.LogInView.as_view(),name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("profile/",views.Profile.as_view({"get":"get"}),name='my_desktop'),
    path("daas/update_usage/",views.UpdateUsage.as_view({"get":"get"}),name="update_usage")
]
urlpatterns+=router.urls
