from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from bika_project import settings
from .models import *

# Dashboard View
@staff_member_required
def admin_dashboard(request):
    """Simplified admin dashboard without complex calculations"""
    # Basic counts only
    total_users = CustomUser.objects.count()
    total_admins = CustomUser.objects.filter(user_type='admin').count()
    total_vendors = CustomUser.objects.filter(user_type='vendor').count()
    total_customers = CustomUser.objects.filter(user_type='customer').count()
    
    total_products = Product.objects.count()
    active_products = Product.objects.filter(status='active').count()
    
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    
    total_categories = ProductCategory.objects.count()
    
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
    
    # Recent data
    recent_products = Product.objects.select_related('vendor', 'category').prefetch_related('images').order_by('-created_at')[:6]
    recent_messages = ContactMessage.objects.filter(status='new').order_by('-submitted_at')[:5]

    # Get Django and Python version
    import django
    import sys
    django_version = django.get_version()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    context = {
        # Basic counts
        'total_users': total_users,
        'total_admins': total_admins,
        'total_vendors': total_vendors,
        'total_customers': total_customers,
        'total_products': total_products,
        'active_products': active_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_categories': total_categories,
        
        # Revenue
        'total_revenue': "{:,.2f}".format(total_revenue),
        'today_revenue': "{:,.2f}".format(today_revenue),
        
        # Percentages
        'admin_percentage': round((total_admins / total_users * 100), 2) if total_users > 0 else 0,
        'vendor_percentage': round((total_vendors / total_users * 100), 2) if total_users > 0 else 0,
        'customer_percentage': round((total_customers / total_users * 100), 2) if total_users > 0 else 0,
        'active_products_percentage': round((active_products / total_products * 100), 2) if total_products > 0 else 0,
        
        # Recent data
        'recent_products': recent_products,
        'recent_messages': recent_messages,
        
        # Other required fields
        'active_users': CustomUser.objects.filter(is_active=True).count(),
        'new_users_today': CustomUser.objects.filter(date_joined__date=timezone.now().date()).count(),
        'draft_products': Product.objects.filter(status='draft').count(),
        'low_stock_products': Product.objects.filter(stock_quantity__lte=5, stock_quantity__gt=0).count(),
        'out_of_stock_products': Product.objects.filter(stock_quantity=0).count(),
        'low_stock_count': Product.objects.filter(stock_quantity__lte=5).count(),
        'active_vendors': CustomUser.objects.filter(user_type='vendor', is_active=True).count(),
        'active_vendors_percentage': round((CustomUser.objects.filter(user_type='vendor', is_active=True).count() / total_vendors * 100), 2) if total_vendors > 0 else 0,
        'active_categories': ProductCategory.objects.filter(is_active=True).count(),
        'active_users_percentage': round((CustomUser.objects.filter(is_active=True).count() / total_users * 100), 2) if total_users > 0 else 0,
        
        # Service stats
        'total_services': Service.objects.count(),
        'total_testimonials': Testimonial.objects.count(),
        'total_messages': ContactMessage.objects.count(),
        'new_messages': ContactMessage.objects.filter(status='new').count(),
        'active_services_count': Service.objects.filter(is_active=True).count(),
        'featured_testimonials_count': Testimonial.objects.filter(is_featured=True, is_active=True).count(),
        'active_faqs_count': FAQ.objects.filter(is_active=True).count(),
        
        # System info
        'django_version': django_version,
        'python_version': python_version,
        'debug': settings.DEBUG,
    }
    
    return render(request, 'bika/pages/admin/dashboard.html', context)

# Admin Model Registrations - USING DECORATORS ONLY (no duplicate registrations)
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'vendor', 'price', 'stock_quantity', 'status', 'created_at']
    list_filter = ['status', 'category', 'vendor', 'created_at']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'is_active', 'display_order']
    list_filter = ['is_active']
    search_fields = ['name']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'user__username']

@admin.register(SiteInfo)
class SiteInfoAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'updated_at']
    readonly_fields = ['updated_at']
    
    def has_add_permission(self, request):
        # Allow only one instance
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['display_order', 'is_active']

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'rating', 'is_featured', 'is_active', 'created_at']
    list_filter = ['is_featured', 'is_active', 'rating', 'created_at']
    search_fields = ['name', 'company', 'content']
    list_editable = ['is_featured', 'is_active']

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'status', 'submitted_at']
    list_filter = ['status', 'submitted_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['submitted_at', 'ip_address']
    actions = ['mark_as_replied', 'mark_as_read']
    
    def mark_as_replied(self, request, queryset):
        for message in queryset:
            message.mark_as_replied()
        self.message_user(request, f"{queryset.count()} messages marked as replied.")
    mark_as_replied.short_description = "Mark selected messages as replied"
    
    def mark_as_read(self, request, queryset):
        queryset.update(status='read')
        self.message_user(request, f"{queryset.count()} messages marked as read.")
    mark_as_read.short_description = "Mark selected messages as read"

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['question', 'answer']
    list_editable = ['display_order', 'is_active']

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'alt_text', 'display_order', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['product__name', 'alt_text']

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__username', 'title']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']
    search_fields = ['order__order_number', 'product__name']

@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'capacity', 'current_occupancy', 'available_capacity', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'address']

@admin.register(ProductDataset)
class ProductDatasetAdmin(admin.ModelAdmin):
    list_display = ['name', 'dataset_type', 'row_count', 'is_active', 'created_at']
    list_filter = ['dataset_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']

@admin.register(TrainedModel)
class TrainedModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'dataset', 'accuracy', 'training_date', 'is_active']
    list_filter = ['model_type', 'is_active', 'training_date']
    search_fields = ['name', 'dataset__name']

@admin.register(RealTimeSensorData)
class RealTimeSensorDataAdmin(admin.ModelAdmin):
    list_display = ['product', 'sensor_type', 'value', 'unit', 'location', 'recorded_at']
    list_filter = ['sensor_type', 'location', 'recorded_at']
    search_fields = ['product__name']
    readonly_fields = ['recorded_at']

@admin.register(ProductAlert)
class ProductAlertAdmin(admin.ModelAdmin):
    list_display = ['product', 'alert_type', 'severity', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_resolved', 'created_at']
    search_fields = ['product__name', 'message']
    readonly_fields = ['created_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']

# Add dashboard to admin URLs
from django.urls import path

def get_admin_urls():
    def wrap(view):
        def wrapper(*args, **kwargs):
            return admin.site.admin_view(view)(*args, **kwargs)
        return wrapper

    return [
        path('dashboard/', wrap(admin_dashboard), name='admin_dashboard'),
    ]

# Override admin site URLs to include dashboard
original_get_urls = admin.site.get_urls

def custom_get_urls():
    return get_admin_urls() + original_get_urls()

admin.site.get_urls = custom_get_urls