# shop/admin.py
from django.contrib import admin
from .models import Order, OrderItem, Product, Size, Review, TrendingClothes, Payment

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total', 'status', 'ordered_at']  # Changed total_price to total
    list_filter = ['status', 'ordered_at']
    search_fields = ['user__username', 'id']
    readonly_fields = ['ordered_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'size', 'price']
    search_fields = ['product__name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price']
    list_filter = ['category']
    search_fields = ['name']
    filter_horizontal = ['sizes']

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['code']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username']

@admin.register(TrendingClothes)
class TrendingClothesAdmin(admin.ModelAdmin):
    list_display = ['product', 'added_on']
    search_fields = ['product__name', 'description']
    list_filter = ['added_on']
    fields = ['product', 'image', 'description']
    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'khalti_pidx', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__id', 'khalti_pidx']