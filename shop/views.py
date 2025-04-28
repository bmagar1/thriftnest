from django.shortcuts import render, redirect,get_object_or_404
from django.http import JsonResponse
from .models import Product, TrendingClothes
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render
from .models import Product,Order,OrderItem
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages

def home(request):
    """ Home page displaying available products """
    products = Product.objects.all()
    trending_clothes = TrendingClothes.objects.all()

    context = {
        'products': products,
        'trending_clothes': trending_clothes
    }

    return render(request, 'shop/home.html', context)


def product_list(request):
    products = Product.objects.all()
    return render(request, 'shop/product_list.html', {'products': products})


def cart(request):
    cart = request.session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render(request, 'shop/cart.html', {'cart': cart, 'total': total})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully! You can now log in.")
            return redirect('login')
        else:
            messages.error(request, "There was an error in your registration.")
    else:
        form = UserCreationForm()
    return render(request, 'shop/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next')  # Retrieve the 'next' parameter from POST data

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to 'next' if available; otherwise, redirect to 'home'
            return redirect(next_url) if next_url else redirect('home')
        else:
            messages.error(request, "Invalid username or password.")

    # For GET requests or failed POST, render the login page
    next_url = request.GET.get('next', '')  # Retrieve the 'next' parameter from GET data
    return render(request, 'shop/login.html', {'next': next_url})

def user_logout(request):
    """ User logout view """
    return redirect('home')

def homepage(request):
    """ Alternative homepage view """
    return render(request, 'shop/home.html')

def products(request):
    products = Product.objects.all()
    men_products = Product.objects.filter(category='Men')
    women_products = Product.objects.filter(category='Women')
    return render(request, 'shop/product_list.html', {
        'products': products,
        'men_products': men_products,
        'women_products': women_products,
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    sizes = product.sizes.all()

    if request.method == 'POST':
        selected_size = request.POST.get('selected_size')
        # You can now use selected_size for processing, like adding to cart
        print("Selected size:", selected_size)

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'sizes': sizes
    })

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = request.session.get('cart', {})
    size = request.POST.get('selected_size', '') or request.GET.get('size', '')
    quantity = int(request.GET.get('quantity', 1))
    key = f"{product_id}_{size}" if size else str(product_id)
    if key in cart:
        cart[key]['quantity'] += quantity
    else:
        cart[key] = {
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'quantity': quantity,
            'size': size,
            'image_url': product.image.url if product.image else ''
        }
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')


def cart_view(request):
    cart = request.session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render(request, 'shop/cart.html', {
        'cart': cart,
        'total': total
    })


def remove_from_cart(request, key):
    cart = request.session.get('cart', {})
    if key in cart:
        del cart[key]
        request.session.modified = True
    return redirect('cart')

def update_cart(request):
    if request.method == 'POST':
        item_key = request.POST.get('item_key')
        action = request.POST.get('action')

        cart = request.session.get('cart', {})
        if item_key in cart:
            if action == 'increase':
                cart[item_key]['quantity'] += 1
            elif action == 'decrease' and cart[item_key]['quantity'] > 1:
                cart[item_key]['quantity'] -= 1

        request.session['cart'] = cart
    return redirect('cart')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty!")
        return redirect('cart')

    total = sum(item['price'] * item['quantity'] for item in cart.values())
    order = Order.objects.create(user=request.user, total_price=total)

    for key, item in cart.items():
        product = get_object_or_404(Product, pk=item['product_id'])
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item['quantity'],
            price=item['price'],
            size=item.get('size', '')
        )

    # Clear the cart
    request.session['cart'] = {}
    request.session.modified = True

    messages.success(request, "Order placed successfully!")
    return redirect('order_detail', order_id=order.id)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'shop/order_detail.html', {'order': order})

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF')
    return response

def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    template_path = 'shop/order_pdf.html'
    context = {'order': order}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors with PDF generation')
    
    return response


def contact(request):
    return render(request, 'shop/contact.html')

def get_involved(request):
    return render(request, 'shop/get_involved.html')

def load_more_products(request):
    start = int(request.GET.get('start', 0))  # Get the start index
    limit = 6  # Number of products to load each time
    products = Product.objects.all()[start:start + limit]
    
    product_list = []
    for product in products:
        product_data = {
            'name': product.name,
            'description': product.description,
            'image_url': product.image.url,
        }
        product_list.append(product_data)

    # Check if there are more products to load
    has_more = Product.objects.count() > start + limit

    return JsonResponse({'products': product_list, 'has_more': has_more})


def shop(request):
    men_products = Product.objects.filter(category='Men')
    women_products = Product.objects.filter(category='Women')

    return render(request, 'shop.html', {
        'men_products': men_products,
        'women_products': women_products,
    })