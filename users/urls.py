from django.urls import path
from .views import (
    MyTokenView,
    RequestMagicLinkView,
    MagicLoginView,
)

app_name = "users"

urlpatterns = [
    path("login/", MyTokenView.as_view(), name="jwt-login"),
    path("magic/request/", RequestMagicLinkView.as_view(), name="magic-request"),
    path("magic/login/", MagicLoginView.as_view(), name="magic-login"),
]
