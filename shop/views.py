from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import Product, TrendingClothes, Order, OrderItem
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

def home(request):
    """Home page displaying trending clothes"""
    trending_clothes = TrendingClothes.objects.all()[:3]  # Limit to 3 items initially
    return render(request, 'shop/home.html', {'trending_clothes': trending_clothes})

def load_more_products(request):
    """AJAX view to load more trending clothes"""
    start = int(request.GET.get('start', 0))
    limit = 3  # Match initial load in home view
    trending_clothes = TrendingClothes.objects.all()[start:start + limit]
    products_data = [
        {
            'id': tc.product.id,
            'name': tc.product.name,
            'description': tc.description or tc.product.description,
            'image_url': tc.image.url if tc.image else tc.product.image.url,
        } for tc in trending_clothes
    ]
    has_more = TrendingClothes.objects.count() > start + limit
    return JsonResponse({'products': products_data, 'has_more': has_more})

def products(request):
    """Product list with Men's and Women's sections"""
    products = Product.objects.all()
    men_products = Product.objects.filter(category='Men')
    women_products = Product.objects.filter(category='Women')
    return render(request, 'shop/product_list.html', {
        'products': products,
        'men_products': men_products,
        'women_products': women_products,
    })

def product_detail(request, pk):
    """Product detail page with size selection"""
    product = get_object_or_404(Product, pk=pk)
    sizes = product.sizes.all()
    if request.method == 'POST':
        selected_size = request.POST.get('selected_size')
        print("Selected size:", selected_size)  # For debugging
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'sizes': sizes
    })

# shop/views.py
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = Product.objects.get(id=product_id)
        size = request.POST.get('size', '')  # Default to empty string if size is missing
        quantity = int(request.POST.get('quantity', 1))
        cart = request.session.get('cart', {})
        item_key = f"{product_id}_{size}" if size else str(product_id)

        # Validate size if product has sizes
        if product.sizes.exists() and not size:
            messages.error(request, f"Please select a size for {product.name}.")
            return redirect('product_detail', pk=product_id)

        if item_key in cart:
            cart[item_key]['quantity'] += quantity
        else:
            cart[item_key] = {
                'product_id': product_id,
                'name': product.name,
                'price': float(product.price),
                'quantity': quantity,
                'size': size or None,  # Store None if size is empty
                'image_url': product.image.url
            }

        request.session['cart'] = cart
        messages.success(request, f"{product.name} added to cart!")
        return redirect('cart')
    return redirect('products')

def cart_view(request):
    """Display cart contents"""
    cart = request.session.get('cart', {})
    total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    return render(request, 'shop/cart.html', {
        'cart': cart,
        'total': total
    })
def remove_from_cart(request, key):
    """Remove item from cart"""
    cart = request.session.get('cart', {})
    if key in cart:
        del cart[key]
        request.session['cart'] = cart
        request.session.modified = True
    return redirect('cart')

def update_cart(request):
    """Update cart item quantity"""
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
        request.session.modified = True
    return redirect('cart')

# shop/views.py
@login_required
def checkout(request):
    """Handle checkout process"""
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    total = sum(float(item['price']) * item['quantity'] for item in cart.values())

    if request.method == 'POST':
        # Collect billing/shipping details
        billing_address = request.POST.get('billing_address')
        shipping_address = request.POST.get('shipping_address', billing_address)

        # Create Order
        order = Order.objects.create(
            user=request.user,
            total=total,
            shipping_address=shipping_address,
            billing_address=billing_address,
            status='pending'
        )

        # Create OrderItems
        for item_key, item in cart.items():
            product = Product.objects.get(id=item['product_id'])
            size = item.get('size')  # Get size, may be None or empty
            if size == '' or size is None:
                size = None  # Ensure empty strings are stored as NULL
            OrderItem.objects.create(
                order=order,
                product=product,
                size=size,
                quantity=item['quantity'],
                price=float(item['price'])
            )

        # Initiate Khalti Payment
        headers = {
            'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            "return_url": settings.KHALTI_RETURN_URL,
            "website_url": settings.WEBSITE_URL,
            "amount": int(total * 100),  # Convert to paisa
            "purchase_order_id": f"order_{order.id}",
            "purchase_order_name": "ThriftNest Order",
            "customer_info": {
                "name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
                "phone": "9800000001"  # Replace with actual user phone or form input
            },
            "product_details": [
                {
                    "identity": str(item['product_id']),
                    "name": item['name'],
                    "total_price": int(float(item['price']) * item['quantity'] * 100),
                    "quantity": item['quantity'],
                    "unit_price": int(float(item['price']) * 100)
                } for item in cart.values()
            ]
        }

        try:
            response = requests.post(settings.KHALTI_INITIATE_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get('pidx'):
                # Create Payment record
                Payment.objects.create(
                    order=order,
                    khalti_pidx=data['pidx'],
                    amount=total,
                    status='pending'
                )
                return redirect(data['payment_url'])
            else:
                messages.error(request, "Failed to initiate payment. Please try again.")
                order.delete()
                return redirect('cart')
        except requests.RequestException as e:
            messages.error(request, f"Payment initiation failed: {str(e)}")
            order.delete()
            return redirect('cart')

    # GET request: Render checkout form
    return render(request, 'shop/checkout.html', {'cart': cart, 'total': total})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = order.payment_set.first()
    return render(request, 'shop/order_detail.html', {
        'order': order,
        'payment': payment
    })

def render_to_pdf(template_src, context_dict={}):
    """Generate PDF from template"""
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF')
    return response

@login_required
def download_invoice(request, order_id):
    """Generate and download invoice PDF"""
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

def register(request):
    """User registration"""
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
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url) if next_url else redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    next_url = request.GET.get('next', '')
    return render(request, 'shop/login.html', {'next': next_url})

def user_logout(request):
    """User logout"""
    logout(request)
    return redirect('home')

def contact(request):
    """Contact page"""
    return render(request, 'shop/contact.html')

def get_involved(request):
    """Get Involved page"""
    return render(request, 'shop/get_involved.html')

def shop(request):
    """Shop page with Men's and Women's products"""
    men_products = Product.objects.filter(category='Men')
    women_products = Product.objects.filter(category='Women')
    return render(request, 'shop.html', {
        'men_products': men_products,
        'women_products': women_products,
    })

import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem, Payment, Product

@login_required
def checkout(request):
    """Handle checkout process"""
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    total = sum(float(item['price']) * item['quantity'] for item in cart.values())

    if request.method == 'POST':
        # Collect billing/shipping details
        billing_address = request.POST.get('billing_address')
        shipping_address = request.POST.get('shipping_address', billing_address)

        # Create Order
        order = Order.objects.create(
            user=request.user,
            total=total,
            shipping_address=shipping_address,
            billing_address=billing_address,
            status='pending'
        )

        # Create OrderItems
        for item_key, item in cart.items():
            product = Product.objects.get(id=item['product_id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                size=item.get('size'),
                quantity=item['quantity'],
                price=item['price']
            )

        # Initiate Khalti Payment
        headers = {
            'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            "return_url": settings.KHALTI_RETURN_URL,
            "website_url": settings.WEBSITE_URL,
            "amount": int(total * 100),  # Convert to paisa
            "purchase_order_id": f"order_{order.id}",
            "purchase_order_name": "ThriftNest Order",
            "customer_info": {
                "name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
                "phone": "9800000001"  # Replace with actual user phone or form input
            },
            "product_details": [
                {
                    "identity": str(item['product_id']),
                    "name": item['name'],
                    "total_price": int(float(item['price']) * item['quantity'] * 100),
                    "quantity": item['quantity'],
                    "unit_price": int(float(item['price']) * 100)
                } for item in cart.values()
            ]
        }

        try:
            response = requests.post(settings.KHALTI_INITIATE_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get('pidx'):
                # Create Payment record
                Payment.objects.create(
                    order=order,
                    khalti_pidx=data['pidx'],
                    amount=total,
                    status='pending'
                )
                return redirect(data['payment_url'])
            else:
                messages.error(request, "Failed to initiate payment. Please try again.")
                order.delete()
                return redirect('cart')
        except requests.RequestException as e:
            messages.error(request, f"Payment initiation failed: {str(e)}")
            order.delete()
            return redirect('cart')

    # GET request: Render checkout form
    return render(request, 'shop/checkout.html', {'cart': cart, 'total': total})

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def payment_success(request):
    """Handle successful payment and generate invoice"""
    pidx = request.GET.get('pidx')
    if not pidx:
        messages.error(request, "Invalid payment response.")
        return redirect('cart')

    # Verify payment with Khalti
    headers = {
        'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(settings.KHALTI_VERIFY_URL, json={'pidx': pidx}, headers=headers)
        response.raise_for_status()
        data = response.json()

        payment = Payment.objects.get(khalti_pidx=pidx)
        order = payment.order

        if data.get('status') == 'Completed':
            payment.status = 'completed'
            payment.save()
            order.status = 'completed'
            order.save()

            # Generate invoice PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
            elements = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                name='Title',
                fontSize=18,
                spaceAfter=12,
                textColor=colors.HexColor('#4e342e'),
                alignment=1  # Center
            )
            subtitle_style = ParagraphStyle(
                name='Subtitle',
                fontSize=12,
                spaceAfter=8,
                textColor=colors.HexColor('#333333')
            )
            normal_style = ParagraphStyle(
                name='Normal',
                fontSize=10,
                spaceAfter=6,
                textColor=colors.HexColor('#333333')
            )

            # Header
            elements.append(Paragraph("Thrift Shop Invoice", title_style))
            elements.append(Paragraph(f"Order #{order.id}", subtitle_style))
            elements.append(Paragraph(f"Date: {order.created.strftime('%Y-%m-%d')}", subtitle_style))
            elements.append(Spacer(1, 12))

            # Customer Information
            elements.append(Paragraph("Customer Details", subtitle_style))
            elements.append(Paragraph(f"Name: {request.user.get_full_name() or request.user.username}", normal_style))
            elements.append(Paragraph(f"Email: {request.user.email}", normal_style))
            elements.append(Spacer(1, 12))

            # Billing and Shipping Addresses
            billing_address = order.billing_address if order.billing_address else "Not provided"
            shipping_address = order.shipping_address if order.shipping_address else "Not provided"
            elements.append(Paragraph("Billing Address", subtitle_style))
            elements.append(Paragraph(billing_address, normal_style))
            elements.append(Paragraph("Shipping Address", subtitle_style))
            elements.append(Paragraph(shipping_address, normal_style))
            elements.append(Spacer(1, 12))

            # Order Items Table
            elements.append(Paragraph("Order Items", subtitle_style))
            data = [['Product', 'Size', 'Quantity', 'Unit Price', 'Total']]
            for item in order.items.all():
                data.append([
                    item.product.name,
                    item.size or 'N/A',
                    str(item.quantity),
                    f"Rs. {item.price:,.2f}",
                    f"Rs. {item.price * item.quantity:,.2f}"
                ])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4e342e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9f1e7')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0cdbd')),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))

            # Payment Details
            elements.append(Paragraph("Payment Details", subtitle_style))
            elements.append(Paragraph(f"Total Amount: Rs. {order.total:,.2f}", normal_style))
            elements.append(Paragraph(f"Payment Status: {payment.status.capitalize()}", normal_style))
            elements.append(Paragraph(f"Khalti Transaction ID: {payment.khalti_pidx}", normal_style))
            elements.append(Paragraph(f"Payment Date: {payment.created.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            elements.append(Spacer(1, 12))

            # Footer
            elements.append(Paragraph("Thank you for shopping with Thrift Nest!", normal_style))
            elements.append(Paragraph("Contact us: support@thriftshop.com | +977-9800000001", normal_style))

            # Build PDF
            doc.build(elements)
            buffer.seek(0)

            # Encode PDF to base64 to pass to template
            import base64
            pdf_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Clear cart
            request.session['cart'] = {}
            messages.success(request, "Payment successful! Your order has been placed.")
            return render(request, 'shop/success.html', {
                'order': order,
                'pdf_data': pdf_data,
                'pdf_filename': f'invoice_order_{order.id}.pdf'
            })
        else:
            payment.status = 'failed'
            payment.save()
            order.status = 'cancelled'
            order.save()
            messages.error(request, "Payment verification failed.")
            return redirect('cart')
    except (requests.RequestException, Payment.DoesNotExist):
        messages.error(request, "Error verifying payment.")
        return redirect('cart')
    
def payment_cancel(request):
    """Handle cancelled payment"""
    messages.error(request, "Payment was cancelled.")
    return render(request, 'shop/cancel.html')


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = order.payment_set.first()  # Get the associated payment

    # Create a PDF response
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        name='Title',
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor('#4e342e'),
        alignment=1  # Center
    )
    subtitle_style = ParagraphStyle(
        name='Subtitle',
        fontSize=12,
        spaceAfter=8,
        textColor=colors.HexColor('#333333')
    )
    normal_style = ParagraphStyle(
        name='Normal',
        fontSize=10,
        spaceAfter=6,
        textColor=colors.HexColor('#333333')
    )

    # Header
    elements.append(Paragraph("Thrift Shop Invoice", title_style))
    elements.append(Paragraph(f"Order #{order.id}", subtitle_style))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%Y-%m-%d')}", subtitle_style))
    elements.append(Spacer(1, 12))

    # Customer Information
    elements.append(Paragraph("Customer Details", subtitle_style))
    elements.append(Paragraph(f"Name: {request.user.get_full_name() or request.user.username}", normal_style))
    elements.append(Paragraph(f"Email: {request.user.email}", normal_style))
    elements.append(Spacer(1, 12))

    # Billing and Shipping Addresses
    elements.append(Paragraph("Billing Address", subtitle_style))
    elements.append(Paragraph(order.billing_address, normal_style))
    elements.append(Paragraph("Shipping Address", subtitle_style))
    elements.append(Paragraph(order.shipping_address, normal_style))
    elements.append(Spacer(1, 12))

    # Order Items Table
    elements.append(Paragraph("Order Items", subtitle_style))
    data = [['Product', 'Size', 'Quantity', 'Unit Price', 'Total']]
    for item in order.items.all():
        data.append([
            item.product.name,
            item.size or 'N/A',
            str(item.quantity),
            f"Rs. {item.price:,.2f}",
            f"Rs. {item.price * item.quantity:,.2f}"
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4e342e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9f1e7')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0cdbd')),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Payment Details
    elements.append(Paragraph("Payment Details", subtitle_style))
    elements.append(Paragraph(f"Total Amount: Rs. {order.total:,.2f}", normal_style))
    if payment:
        elements.append(Paragraph(f"Payment Status: {payment.status.capitalize()}", normal_style))
        elements.append(Paragraph(f"Khalti Transaction ID: {payment.khalti_pidx}", normal_style))
        elements.append(Paragraph(f"Payment Date: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    else:
        elements.append(Paragraph("Payment Status: Pending", normal_style))
    elements.append(Spacer(1, 12))

    # Footer
    elements.append(Paragraph("Thank you for shopping with Thrift Nest!", normal_style))
    elements.append(Paragraph("Contact us: support@thriftshop.com | +977-9800000001", normal_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    # Serve PDF as download
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=invoice_order_{order.id}.pdf'
    return response