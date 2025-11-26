from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q, F  # ADD F HERE
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
# api_views.py - REAL IMPLEMENTATION
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import pandas as pd

from bika.notification import RealNotificationService
from bika.service import RealProductAIService

# Import models
from .models import (
    Notification, ProductAlert, ProductDataset, RealTimeSensorData, SiteInfo, Service, StorageLocation, Testimonial, ContactMessage, FAQ,
    CustomUser, Product, ProductCategory, ProductImage, ProductReview,
    Wishlist, Cart, Order, OrderItem
)

# Import forms
from .forms import (
    ContactForm, NewsletterForm, CustomUserCreationForm, 
    VendorRegistrationForm, CustomerRegistrationForm, ProductForm,
    ProductImageForm
)
from bika import models

from .models import (
    ProductDataset, SiteInfo, Service, Testimonial, ContactMessage, FAQ,
    CustomUser, Product, ProductCategory, ProductImage, ProductReview,
    Wishlist, Cart, Order, OrderItem, StorageLocation, ProductAlert, 
    Notification, RealTimeSensorData, TrainedModel  # ADD THESE
)
# ... other imports ...

try:
    from bika.notification import RealNotificationService
    from bika.service import RealProductAIService
    AI_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"AI services not available: {e}")
    AI_SERVICES_AVAILABLE = False
    # Create dummy classes for fallback
    class RealNotificationService:
        def __init__(self):
            pass
        def run_daily_analysis(self):
            print("AI services not available - running in fallback mode")
    
    class RealProductAIService:
        def __init__(self):
            pass

class HomeView(TemplateView):
    template_name = 'bika/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Existing services and testimonials
        context['featured_services'] = Service.objects.filter(is_active=True)[:6]
        context['featured_testimonials'] = Testimonial.objects.filter(
            is_active=True, 
            is_featured=True
        )[:3]
        context['faqs'] = FAQ.objects.filter(is_active=True)[:5]
        
        # Add featured products with error handling
        try:
            featured_products = Product.objects.filter(
                status='active',
                is_featured=True
            ).select_related('category', 'vendor')[:8]
            
            # Add primary images to products
            for product in featured_products:
                try:
                    product.primary_image = product.images.filter(is_primary=True).first()
                    if not product.primary_image:
                        product.primary_image = product.images.first()
                except Exception:
                    product.primary_image = None
            
            context['featured_products'] = featured_products
            
        except Exception as e:
            print(f"Error loading featured products: {e}")
            context['featured_products'] = []
        
        # Add site info if available
        try:
            context['site_info'] = SiteInfo.objects.first()
        except Exception:
            context['site_info'] = None
        
        return context

def about_view(request):
    services = Service.objects.filter(is_active=True)
    testimonials = Testimonial.objects.filter(is_active=True)[:4]
    
    context = {
        'services': services,
        'testimonials': testimonials,
    }
    return render(request, 'bika/pages/about.html', context)

def services_view(request):
    services = Service.objects.filter(is_active=True)
    return render(request, 'bika/pages/services.html', {'services': services})

class ServiceDetailView(DetailView):
    model = Service
    template_name = 'bika/pages/service_detail.html'
    context_object_name = 'service'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save(commit=False)
            
            # Get client IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                contact_message.ip_address = x_forwarded_for.split(',')[0]
            else:
                contact_message.ip_address = request.META.get('REMOTE_ADDR')
            
            contact_message.save()
            
            # Send email notification (optional)
            try:
                send_mail(
                    f'New Contact Message: {contact_message.subject}',
                    f'''
                    Name: {contact_message.name}
                    Email: {contact_message.email}
                    Phone: {contact_message.phone}
                    
                    Message:
                    {contact_message.message}
                    ''',
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email error: {e}")
            
            messages.success(
                request, 
                'Thank you for your message! We will get back to you soon.'
            )
            return redirect('bika:contact')
    else:
        form = ContactForm()
    
    return render(request, 'bika/pages/contact.html', {'form': form})

def faq_view(request):
    faqs = FAQ.objects.filter(is_active=True)
    return render(request, 'bika/pages/faq.html', {'faqs': faqs})

def newsletter_subscribe(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            return JsonResponse({
                'success': True,
                'message': 'Thank you for subscribing to our newsletter!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid email address.'
            })
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@staff_member_required
def admin_dashboard(request):
    """Enhanced admin dashboard with user and product statistics"""
    # Get current date and time
    now = timezone.now()
    today = now.date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    thirty_days_ago = now - timedelta(days=30)

    # User Statistics
    total_users = CustomUser.objects.count()
    total_admins = CustomUser.objects.filter(user_type='admin').count()
    total_vendors = CustomUser.objects.filter(user_type='vendor').count()
    total_customers = CustomUser.objects.filter(user_type='customer').count()
    
    # Calculate percentages
    admin_percentage = round((total_admins / total_users * 100), 2) if total_users > 0 else 0
    vendor_percentage = round((total_vendors / total_users * 100), 2) if total_users > 0 else 0
    customer_percentage = round((total_customers / total_users * 100), 2) if total_users > 0 else 0
    
    # Active users (logged in last 30 days)
    active_users = CustomUser.objects.filter(last_login__gte=thirty_days_ago).count()
    active_users_percentage = round((active_users / total_users * 100), 2) if total_users > 0 else 0
    
    # New users today
    new_users_today = CustomUser.objects.filter(date_joined__gte=today_start).count()

    # Product Statistics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(status='active').count()
    draft_products = Product.objects.filter(status='draft').count()
    
    # Calculate active products percentage
    active_products_percentage = round((active_products / total_products * 100), 2) if total_products > 0 else 0
    
    # Inventory alerts - FIXED: Use F() directly (not models.F)
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=F('low_stock_threshold'),  # CHANGED: models.F to F
        track_inventory=True,
        stock_quantity__gt=0
    ).count()
    
    out_of_stock_products = Product.objects.filter(
        stock_quantity=0,
        track_inventory=True
    ).count()
    
    low_stock_count = low_stock_products + out_of_stock_products

    # Vendor Statistics
    active_vendors = CustomUser.objects.filter(
        user_type='vendor', 
        is_active=True,
        product__status='active'
    ).distinct().count()
    
    active_vendors_percentage = round((active_vendors / total_vendors * 100), 2) if total_vendors > 0 else 0

    # Order Statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    
    # Calculate revenue manually without SUM
    total_revenue = 0
    today_revenue = 0
    
    # Calculate total revenue manually
    all_orders = Order.objects.all()
    for order in all_orders:
        if order.total_amount:
            try:
                total_revenue += float(order.total_amount)
            except (TypeError, ValueError):
                continue
    
    # Calculate today's revenue
    today_orders = Order.objects.filter(created_at__gte=today_start)
    for order in today_orders:
        if order.total_amount:
            try:
                today_revenue += float(order.total_amount)
            except (TypeError, ValueError):
                continue

    # Format revenue for display
    total_revenue_display = "{:,.2f}".format(total_revenue)
    today_revenue_display = "{:,.2f}".format(today_revenue)

    # Category Statistics
    total_categories = ProductCategory.objects.count()
    active_categories = ProductCategory.objects.filter(is_active=True).count()

    # Recent data
    recent_products = Product.objects.select_related('vendor', 'category').prefetch_related('images').order_by('-created_at')[:6]
    recent_messages = ContactMessage.objects.filter(status='new').order_by('-submitted_at')[:5]

    # Existing stats for compatibility
    total_services = Service.objects.count()
    total_testimonials = Testimonial.objects.count()
    total_messages = ContactMessage.objects.count()
    new_messages = ContactMessage.objects.filter(status='new').count()
    active_services_count = Service.objects.filter(is_active=True).count()
    featured_testimonials_count = Testimonial.objects.filter(is_featured=True, is_active=True).count()
    active_faqs_count = FAQ.objects.filter(is_active=True).count()

    # Get Django and Python version dynamically
    import django
    import sys
    django_version = django.get_version()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    context = {
        # Enhanced User Stats
        'total_users': total_users,
        'total_admins': total_admins,
        'total_vendors': total_vendors,
        'total_customers': total_customers,
        'admin_percentage': admin_percentage,
        'vendor_percentage': vendor_percentage,
        'customer_percentage': customer_percentage,
        'active_users': active_users,
        'active_users_percentage': active_users_percentage,
        'new_users_today': new_users_today,
        
        # Enhanced Product Stats
        'total_products': total_products,
        'active_products': active_products,
        'active_products_percentage': active_products_percentage,
        'draft_products': draft_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'low_stock_count': low_stock_count,
        
        # Vendor Stats
        'active_vendors': active_vendors,
        'active_vendors_percentage': active_vendors_percentage,
        
        # Order Stats
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_revenue': total_revenue_display,
        'today_revenue': today_revenue_display,
        
        # Category Stats
        'total_categories': total_categories,
        'active_categories': active_categories,
        
        # Recent Data
        'recent_products': recent_products,
        'recent_messages': recent_messages,
        
        # Existing stats for compatibility
        'total_services': total_services,
        'total_testimonials': total_testimonials,
        'total_messages': total_messages,
        'new_messages': new_messages,
        'active_services_count': active_services_count,
        'featured_testimonials_count': featured_testimonials_count,
        'active_faqs_count': active_faqs_count,
        
        # System info
        'django_version': django_version,
        'python_version': python_version,
        'debug': settings.DEBUG,
    }
    
    return render(request, 'bika/pages/admin/dashboard.html', context)

def product_list_view(request):
    """Display all active products with filtering and pagination"""
    products = Product.objects.filter(status='active').select_related('category', 'vendor')
    
    # Get filter parameters
    category_slug = request.GET.get('category')
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'newest')
    
    # Filter by category
    current_category = None
    if category_slug:
        try:
            current_category = ProductCategory.objects.get(slug=category_slug, is_active=True)
            products = products.filter(category=current_category)
        except ProductCategory.DoesNotExist:
            pass
    
    # Search functionality
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(short_description__icontains=query) |
            Q(tags__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:  # newest
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    # Get categories for sidebar
    categories = ProductCategory.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__status='active'))
    )
    
    # Count active vendors
    active_vendors = CustomUser.objects.filter(
        user_type='vendor', 
        product__status='active'
    ).distinct().count()
    
    context = {
        'products': page_obj,
        'categories': categories,
        'current_category': current_category,
        'query': query,
        'total_products': products.count(),
        'active_vendors': active_vendors,
    }
    return render(request, 'bika/pages/products.html', context)

def product_detail_view(request, slug):
    """Display single product details"""
    product = get_object_or_404(Product, slug=slug, status='active')
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        status='active'
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'bika/pages/product_detail.html', context)

def products_by_category_view(request, category_slug):
    """Display products by category"""
    category = get_object_or_404(ProductCategory, slug=category_slug, is_active=True)
    products = Product.objects.filter(category=category, status='active')
    
    # Get categories for sidebar
    categories = ProductCategory.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__status='active'))
    )
    
    context = {
        'category': category,
        'products': products,
        'categories': categories,
        'current_category': category,
        'total_products': products.count(),
    }
    return render(request, 'bika/pages/products.html', context)

def product_search_view(request):
    """Handle product search"""
    query = request.GET.get('q', '')
    products = Product.objects.filter(status='active')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(short_description__icontains=query) |
            Q(tags__icontains=query)
        )
    
    context = {
        'products': products,
        'query': query,
        'categories': ProductCategory.objects.filter(is_active=True),
    }
    return render(request, 'bika/pages/product_search.html', context)

@login_required
def vendor_dashboard(request):
    """Vendor dashboard"""
    if not request.user.is_vendor() and not request.user.is_staff:
        messages.error(request, "Access denied. Vendor account required.")
        return redirect('bika:home')
    
    # Get vendor's products (for staff, show all products)
    if request.user.is_staff:
        vendor_products = Product.objects.all()
    else:
        vendor_products = Product.objects.filter(vendor=request.user)
    
    # Recent orders (you'll need to implement this based on your Order model)
    recent_orders = Order.objects.none()  # Placeholder
    
    context = {
        'total_products': vendor_products.count(),
        'active_products': vendor_products.filter(status='active').count(),
        'draft_products': vendor_products.filter(status='draft').count(),
        'recent_products': vendor_products.order_by('-created_at')[:5],
        'recent_orders': recent_orders,
    }
    return render(request, 'bika/pages/vendor/dashboard.html', context)

@login_required
def vendor_product_list(request):
    """Vendor's product list"""
    if not request.user.is_vendor() and not request.user.is_staff:
        messages.error(request, "Access denied. Vendor account required.")
        return redirect('bika:home')
    
    # For staff, show all products; for vendors, show only their products
    if request.user.is_staff:
        products = Product.objects.all()
    else:
        products = Product.objects.filter(vendor=request.user)
    
    context = {
        'products': products,
    }
    return render(request, 'bika/pages/vendor/products.html', context)

@login_required
def vendor_add_product(request):
    """Vendor add product form with multiple image upload"""
    # Allow both vendors and staff to add products
    if not request.user.is_vendor() and not request.user.is_staff:
        messages.error(request, "Access denied. Vendor or admin account required.")
        return redirect('bika:home')
    
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)
        
        if product_form.is_valid():
            # Save product with vendor
            product = product_form.save(commit=False)
            product.vendor = request.user
            
            # Set status based on button clicked
            if 'save_draft' in request.POST:
                product.status = 'draft'
                message = f'Product "{product.name}" saved as draft!'
            else:  # publish button
                product.status = 'active'
                message = f'Product "{product.name}" published successfully!'
            
            product.save()
            
            # Handle multiple images
            images = request.FILES.getlist('images')
            for i, image in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    alt_text=product.name,
                    display_order=i,
                    is_primary=(i == 0)  # First image is primary
                )
            
            messages.success(request, message)
            return redirect('bika:vendor_product_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Set initial status to draft for new products
        product_form = ProductForm(initial={'status': 'draft', 'condition': 'new'})
    
    context = {
        'form': product_form,
        'title': 'Add New Product'
    }
    return render(request, 'bika/pages/vendor/add_product.html', context)

@login_required
def vendor_edit_product(request, product_id):
    """Edit existing product"""
    # For staff, allow editing any product; for vendors, only their own products
    if request.user.is_staff:
        product = get_object_or_404(Product, id=product_id)
    else:
        product = get_object_or_404(Product, id=product_id, vendor=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('bika:vendor_product_list')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'title': 'Edit Product'
    }
    return render(request, 'bika/pages/vendor/add_product.html', context)

def vendor_register_view(request):
    """Special vendor registration"""
    # Only redirect logged-in users who are ALREADY vendors
    if request.user.is_authenticated and request.user.is_vendor():
        messages.info(request, "You are already a registered vendor!")
        return redirect('bika:vendor_dashboard')
    
    # Show warning for logged-in customers but still show the form
    if request.user.is_authenticated and not request.user.is_vendor():
        messages.warning(request, "You already have a customer account. Please contact support to convert to vendor.")
    
    if request.method == 'POST':
        form = VendorRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Auto-login after registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Vendor account created successfully! Welcome to Bika, {user.business_name}.")
                return redirect('bika:vendor_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VendorRegistrationForm()
    
    return render(request, 'bika/pages/registration/vendor_register.html', {'form': form})

def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in!")
        return redirect('bika:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Auto-login after registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Account created successfully! Welcome to Bika, {username}.')
                return redirect('bika:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'bika/pages/registration/register.html', {'form': form})

# User profile views (keep your existing implementations)
@login_required
def user_profile(request):
    """User profile page"""
    user = request.user
    recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:5]
    
    context = {
        'user': user,
        'recent_orders': recent_orders,
    }
    return render(request, 'bika/pages/user/profile.html', context)

@login_required
def update_profile(request):
    """Update user profile"""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.address = request.POST.get('address', user.address)
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('bika:user_profile')
    
    return redirect('bika:user_profile')

@login_required
def user_orders(request):
    """User orders page"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'bika/pages/user/orders.html', context)

@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'bika/pages/user/order_detail.html', context)

@login_required
def wishlist(request):
    """User wishlist page"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'bika/pages/user/wishlist.html', context)

@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Product added to wishlist!',
            'wishlist_count': Wishlist.objects.filter(user=request.user).count()
        })
    
    messages.success(request, 'Product added to wishlist!')
    return redirect('bika:wishlist')

@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Product removed from wishlist!',
            'wishlist_count': Wishlist.objects.filter(user=request.user).count()
        })
    
    messages.success(request, 'Product removed from wishlist!')
    return redirect('bika:wishlist')

@login_required
def cart(request):
    """Shopping cart page"""
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    total_price = sum(item.total_price for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'bika/pages/user/cart.html', context)

@login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_count = Cart.objects.filter(user=request.user).count()
        return JsonResponse({
            'success': True,
            'message': 'Product added to cart!',
            'cart_count': cart_count
        })
    
    messages.success(request, 'Product added to cart!')
    return redirect('bika:cart')

@login_required
def update_cart(request, product_id):
    """Update cart item quantity"""
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart_item = get_object_or_404(Cart, user=request.user, product=product)
        cart_item.quantity = quantity
        cart_item.save()
    else:
        Cart.objects.filter(user=request.user, product=product).delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_items = Cart.objects.filter(user=request.user)
        total_price = sum(item.total_price for item in cart_items)
        return JsonResponse({
            'success': True,
            'total_price': total_price,
            'item_total': cart_item.total_price if quantity > 0 else 0
        })
    
    return redirect('bika:cart')

@login_required
def remove_from_cart(request, product_id):
    """Remove product from cart"""
    product = get_object_or_404(Product, id=product_id)
    Cart.objects.filter(user=request.user, product=product).delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_items = Cart.objects.filter(user=request.user)
        total_price = sum(item.total_price for item in cart_items)
        return JsonResponse({
            'success': True,
            'total_price': total_price,
            'cart_count': cart_items.count()
        })
    
    messages.success(request, 'Product removed from cart!')
    return redirect('bika:cart')

@login_required
def user_settings(request):
    """User settings page"""
    if request.method == 'POST':
        # Handle settings update
        user = request.user
        user.email_notifications = request.POST.get('email_notifications') == 'on'
        user.sms_notifications = request.POST.get('sms_notifications') == 'on'
        user.newsletter_subscription = request.POST.get('newsletter_subscription') == 'on'
        user.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('bika:user_settings')
    
    context = {
        'user': request.user,
    }
    return render(request, 'bika/pages/user/settings.html', context)

# Error handlers
def handler404(request, exception):
    return render(request, 'bika/pages/404.html', status=404)

def handler500(request):
    return render(request, 'bika/pages/500.html', status=500)

def custom_404(request, exception):
    return render(request, 'bika/pages/404.html', status=404)

def custom_500(request):
    return render(request, 'bika/pages/500.html', status=500)



@csrf_exempt
@require_http_methods(["POST"])
def upload_dataset(request):
    """Upload real dataset for training"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        dataset_file = request.FILES['dataset_file']
        dataset_type = request.POST['dataset_type']
        name = request.POST['name']
        description = request.POST.get('description', '')
        
        # Validate file type
        if not dataset_file.name.endswith('.csv'):
            return JsonResponse({'error': 'Only CSV files are supported'}, status=400)
        
        # Read and validate dataset
        df = pd.read_csv(dataset_file)
        
        # Create dataset record
        dataset = ProductDataset.objects.create(
            name=name,
            dataset_type=dataset_type,
            description=description,
            data_file=dataset_file,
            columns=list(df.columns),
            row_count=len(df)
        )
        
        return JsonResponse({
            'success': True,
            'dataset_id': dataset.id,
            'columns': list(df.columns),
            'row_count': len(df)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def train_model(request):
    """Train model on uploaded dataset"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        dataset_id = data['dataset_id']
        model_type = data['model_type']
        
        ai_service = RealProductAIService()
        trained_model = ai_service.train_anomaly_detection_model(dataset_id)
        
        if trained_model:
            return JsonResponse({
                'success': True,
                'model_id': trained_model.id,
                'model_name': trained_model.name
            })
        else:
            return JsonResponse({'error': 'Model training failed'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def receive_sensor_data(request):
    """Receive real sensor data from embedded systems"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['product_barcode', 'sensor_type', 'value', 'location_id']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Missing field: {field}'}, status=400)
        
        # Get product and location
        product = Product.objects.get(barcode=data['product_barcode'])
        location = StorageLocation.objects.get(id=data['location_id'])
        
        # Save sensor reading
        sensor_reading = RealTimeSensorData.objects.create(
            product=product,
            sensor_type=data['sensor_type'],
            value=data['value'],
            unit=data.get('unit', ''),
            location=location
        )
        
        # Analyze for alerts
        ai_service = RealProductAIService()
        alerts = ai_service.analyze_sensor_data([sensor_reading])
        
        # Process alerts
        if alerts:
            notification_service = RealNotificationService()
            notification_service.process_sensor_alerts(alerts)
        
        return JsonResponse({'status': 'success', 'alerts_generated': len(alerts)})
        
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except StorageLocation.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
# Add these to your views.py

@login_required
def notifications_view(request):
    """User notifications page"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'bika/pages/user/notifications.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('bika:notifications')

@login_required
def unread_notifications_count(request):
    """API endpoint for unread notifications count"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        critical_count = Notification.objects.filter(
            user=request.user, 
            is_read=False,
            notification_type='urgent_alert'
        ).count()
        
        return JsonResponse({
            'unread_count': unread_count,
            'critical_count': critical_count
        })
    return JsonResponse({'unread_count': 0, 'critical_count': 0})

@staff_member_required
def storage_sites(request):
    """Storage sites management"""
    sites = StorageLocation.objects.all()
    
    context = {
        'sites': sites,
    }
    return render(request, 'bika/pages/admin/storage_sites.html', context)

@login_required
def track_my_products(request):
    """Track vendor's products"""
    if not request.user.is_vendor() and not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('bika:home')
    
    # Get vendor's products with alerts
    if request.user.is_staff:
        products = Product.objects.all()
        alerts = ProductAlert.objects.filter(is_resolved=False)
    else:
        products = Product.objects.filter(vendor=request.user)
        alerts = ProductAlert.objects.filter(product__vendor=request.user, is_resolved=False)
    
    context = {
        'products': products,
        'alerts': alerts,
    }
    return render(request, 'bika/pages/vendor/track_products.html', context)

@login_required
def scan_product(request):
    """Product scanning interface"""
    return render(request, 'bika/pages/scan_product.html')

# API endpoints for mobile/scanner integration
@csrf_exempt
@require_http_methods(["GET"])
def api_product_detail(request, barcode):
    """API endpoint for product details by barcode"""
    try:
        product = Product.objects.get(barcode=barcode)
        product_data = {
            'id': product.id,
            'name': product.name,
            'barcode': product.barcode,
            'sku': product.sku,
            'price': str(product.price),
            'stock_quantity': product.stock_quantity,
            'status': product.status,
            'vendor': product.vendor.business_name,
            'category': product.category.name,
        }
        return JsonResponse(product_data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'All notifications marked as read!')
    return redirect('bika:notifications')

@login_required
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Notification deleted!')
    return redirect('bika:notifications')