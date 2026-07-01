from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('dashboard-old/', views.home, name='home_old'),
    path('browse/', views.browse_catalogue, name='browse_catalogue'),
    path('catalogue/', views.browse_catalogue, name='catalogue_search'),
    path('map/', views.map_view, name='map_view'),
    path('analytics/', views.admin_analytics_dashboard, name='admin_analytics_dashboard'),
    path('profile/', views.admin_profile_view, name='admin_profile'),
    path('governance/', views.governance_dashboard_view, name='governance_dashboard'),
    path('governance-policy/', views.governance_policy_view, name='governance_policy'),
    path('register/', views.register_dataset, name='register_dataset'),
    path('dataset/<int:dataset_id>/', views.dataset_detail_view, name='dataset_detail'),
    path('dataset/<int:pk>/download/', views.dataset_download, name='dataset_download'),
]
