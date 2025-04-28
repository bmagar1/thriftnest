from django.contrib import admin
from .models import Product, Order, TrendingClothes,Size

admin.site.register(Product)
admin.site.register(Order)
admin.site.register(TrendingClothes)
admin.site.register(Size)

admin.site.site_header = "ThriftNest Admin Panel"
admin.site.site_title = "ThriftNest Admin"
admin.site.index_title = "Welcome to ThriftNest"