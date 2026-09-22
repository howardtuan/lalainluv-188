from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('', views.order_list, name='order_list'),
    path('wish/', views.wish_list, name='wish_list'),
    path('wish/create/', views.wish_create, name='wish_create'),
    path('wish/<int:pk>/image/', views.wish_image, name='wish_image'),
    path('<str:order_number>/', views.order_detail, name='order_detail'),
]
