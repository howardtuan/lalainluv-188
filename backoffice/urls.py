from django.urls import path
from . import views

app_name = 'backoffice'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('logout/', views.StaffLogoutView.as_view(), name='logout'),
    path('products/', views.products, name='products'),
    path('products/new/', views.product_edit, name='product_create'),
    path('products/<int:pk>/', views.product_edit, name='product_edit'),
    path('orders/', views.orders, name='orders'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('banners/', views.banners, name='banners'),
    path('banners/new/', views.banner_edit, name='banner_create'),
    path('banners/<int:pk>/', views.banner_edit, name='banner_edit'),
    path('categories/', views.categories, name='categories'),
    path('categories/new/', views.category_edit, name='category_create'),
    path('categories/<int:pk>/', views.category_edit, name='category_edit'),
    path('wishes/', views.wishes, name='wishes'),
    path('wishes/<int:pk>/', views.wish_edit, name='wish_edit'),
    path('settings/', views.site_settings, name='settings'),
]
