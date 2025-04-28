from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

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
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='trending', null=True, blank=True)
    image = models.ImageField(upload_to='trending_clothes/')
    description = models.TextField(blank=True, null=True)
    added_on = models.DateField(auto_now_add=True)
    def __str__(self):
        return self.product.name if self.product else self.name

# Order Model
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')],
        default='Pending'
    )
    ordered_at = models.DateTimeField(default=now)
    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

# Order Item Model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=4, choices=SIZE_CHOICES, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Size: {self.size})"