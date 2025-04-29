from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.products, name='products'),  
    path('contact/', views.contact, name='contact'),
    path('get-involved/', views.get_involved, name='get_involved'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),  
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('remove-from-cart/<str:key>/', views.remove_from_cart, name='remove_from_cart'),
    path('update_cart/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/download_invoice/', views.download_invoice, name='download_invoice'),
    path('load_more_products/', views.load_more_products, name='load_more_products'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('order/<int:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    path('search/', views.search_products, name='search_products'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
