from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.conf import settings

# Choices for Size
SIZE_CHOICES = [
    ('S', 'Small'),
    ('M', 'Medium'),
    ('L', 'Large'),
    ('XL', 'Extra Large'),
    ('XXL', 'Double XL'),
]

# Size Model
class Size(models.Model):
    code = models.CharField(max_length=4, choices=SIZE_CHOICES, unique=True)
    def __str__(self):
        return dict(SIZE_CHOICES).get(self.code, self.code)

# Product Model
class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Men', 'Men'),
        ('Women', 'Women'),
    ]
    name = models.CharField(max_length=200)
    description = models.TextField(default='No description available')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    sizes = models.ManyToManyField(Size, related_name='products', blank=True)

    def __str__(self):
        return self.name

# Customer Review Model
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"

# Trending Clothes Model
class TrendingClothes(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='trending', null=False, blank=False)
    image = models.ImageField(upload_to='trending_clothes/')
    description = models.TextField(blank=True, null=True)
    added_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.product.name

    def clean(self):
        if not self.product:
            raise ValidationError("A product must be selected.")
        if self.product.category not in dict(self.product.CATEGORY_CHOICES):
            raise ValidationError("Product must have a valid category (Men or Women).")
        if not self.product.sizes.exists():
            raise ValidationError("Product must have at least one size assigned.")

# Order Model
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Changed from total_price
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')],
        default='Pending'
    )
    ordered_at = models.DateTimeField(default=now)
    shipping_address = models.TextField(blank=True, null=True)  # Added for Khalti
    billing_address = models.TextField(blank=True, null=True)  # Added for Khalti
    created = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

# shop/models.py
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=4, choices=SIZE_CHOICES, blank=True, null=True)  # Allow null
    price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Size: {self.size or 'N/A'})"
    
class Payment(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    khalti_pidx = models.CharField(max_length=100)  # Store Khalti's pidx
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    created = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"Payment for Order {self.order.id}"