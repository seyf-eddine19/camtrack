from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # تسجيل الدخول والخروج
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Contract
    path('contracts/', views.ContractListView.as_view(), name='contract_list'),
    path('contracts/<str:pk>/detail', views.ContractDetailView.as_view(), name='contract_detail'),
    path('contracts/add/', views.ContractFormView.as_view(), name='contract_add'),
    path('contracts/<str:pk>/edit/', views.ContractFormView.as_view(), name='contract_edit'),
    path('contracts/<str:pk>/delete/', views.ContractDeleteView.as_view(), name='contract_delete'),
    
    # Device Categories
    path('device-categories/', views.manage_device_categories, name='manage_device_categories'),

    # Warehouse
    path('warehouses/', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('warehouses/<int:pk>/detail', views.WarehouseDetailView.as_view(), name='warehouse_detail'),

    # Devices
    path('warehouses/<int:warehouse_id>/devices/add', views.DeviceFormView.as_view(), name='device_add'),
    path('warehouses/devices/<int:pk>/detail', views.DeviceDetailView.as_view(), name='device_detail'),
    path('warehouses/devices/<int:pk>/edit', views.DeviceFormView.as_view(), name='device_edit'),
    path('warehouses/devices/<int:pk>/delete', views.DeviceDeleteView.as_view(), name='device_delete'),
    path('warehouses/devices/<int:pk>/status', views.update_device_status, name='update_device_status'),
    path("import/devices/", views.DeviceImportView.as_view(), name="import_devices"),

    # Maintenance 
    path('maintenance/', views.MaintenanceListView.as_view(), name='maintenance_list'),
    path('maintenance/devices/<int:device_id>/add/', views.MaintenanceCreateView.as_view(), name='maintenance_add'),
    path('maintenance/<int:pk>/edit/', views.MaintenanceUpdateView.as_view(), name='maintenance_edit'),
    path('maintenance/<int:pk>/delete/', views.MaintenanceDeleteView.as_view(), name='maintenance_delete'),

    # Task
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/<int:pk>/change-status/<str:status>/', views.task_change_status, name='task_change_status'),
    path('tasks/add/', views.TaskCreateView.as_view(), name='task_add'),
    path('tasks/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_edit'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),

    # Coordination Request
    path('coordination/', views.CoordinationListView.as_view(), name='coordination_list'),
    path('coordination/add/', views.CoordinationCreateView.as_view(), name='coordination_add'),
    path('coordination/<int:pk>/edit/', views.CoordinationUpdateView.as_view(), name='coordination_edit'),
    path('coordination/<int:pk>/delete/', views.CoordinationDeleteView.as_view(), name='coordination_delete'),
]
