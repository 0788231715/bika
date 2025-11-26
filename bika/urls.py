from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'bika'

urlpatterns = [
    # Main pages
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.about_view, name='about'),
    path('services/', views.services_view, name='services'),
    path('services/<slug:slug>/', views.ServiceDetailView.as_view(), name='service_detail'),
    path('contact/', views.contact_view, name='contact'),
    path('faq/', views.faq_view, name='faq'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(
        template_name='bika/pages/registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        template_name='bika/pages/registration/logout.html'
    ), name='logout'),
    
    path('register/', views.register_view, name='register'),
    
    # Product URLs
    path('products/', views.product_list_view, name='product_list'),
    path('products/category/<slug:category_slug>/', views.products_by_category_view, name='products_by_category'),
    path('products/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('products/search/', views.product_search_view, name='product_search'),
    
    # Vendor URLs
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/products/', views.vendor_product_list, name='vendor_product_list'),
    path('vendor/products/add/', views.vendor_add_product, name='vendor_add_product'),
    path('vendor/products/edit/<int:product_id>/', views.vendor_edit_product, name='vendor_edit_product'),
    path('vendor/register/', views.vendor_register_view, name='vendor_register'),
    
    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='bika/pages/registration/password_reset.html',
             email_template_name='bika/pages/registration/password_reset_email.html',
             subject_template_name='bika/pages/registration/password_reset_subject.txt',
             success_url='/password-reset/done/'
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='bika/pages/registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='bika/pages/registration/password_reset_confirm.html',
             success_url='/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='bika/pages/registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),

    # User Profile URLs
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('orders/', views.user_orders, name='user_orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('settings/', views.user_settings, name='user_settings'),
    # Notification URLs
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/unread-count/', views.unread_notifications_count, name='unread_notifications_count'),
    
    # Storage and Tracking URLs
    path('storage-sites/', views.storage_sites, name='storage_sites'),
    path('track-products/', views.track_my_products, name='track_my_products'),
    path('scan-product/', views.scan_product, name='scan_product'),
    
    # API URLs
    path('api/product/<str:barcode>/', views.api_product_detail, name='api_product_detail'),
    
    # AI Service URLs
    path('api/upload-dataset/', views.upload_dataset, name='upload_dataset'),
    path('api/train-model/', views.train_model, name='train_model'),
    path('api/sensor-data/', views.receive_sensor_data, name='receive_sensor_data'),
    # Add these to your urlpatterns
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    
    # AJAX/API endpoints
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
]