from django.db import transaction
from datetime import datetime, timedelta

from bika.models import CustomUser, Product, ProductAlert, Notification
from bika.service import RealProductAIService

class RealNotificationService:
    def __init__(self):
        self.ai_service = RealProductAIService()
    
    def run_daily_analysis(self):
        """Run daily analysis on all products"""
        print("Starting daily product analysis...")
        
        # Get all active products
        products = Product.objects.filter(status='active')
        
        # Detect anomalies
        anomalies = self.ai_service.detect_product_anomalies(products)
        
        # Create alerts for anomalies
        for anomaly in anomalies:
            try:
                product = Product.objects.get(id=anomaly['product_id'])
                self.create_product_alert(
                    product=product,
                    alert_type='ai_anomaly',
                    severity='high',
                    message=f"AI detected anomaly in product data. {anomaly.get('reason', 'Score: ' + str(anomaly.get('anomaly_score', 'N/A')))}",
                    detected_by='ai_system'
                )
            except Product.DoesNotExist:
                continue
        
        # Check stock levels
        self.check_stock_levels()
        
        # Check expiry dates
        self.check_expiry_dates()
        
        print(f"Daily analysis completed. Found {len(anomalies)} anomalies.")
    
    def check_stock_levels(self):
        """Check stock levels and create alerts"""
        low_stock_products = Product.objects.filter(
            track_inventory=True,
            stock_quantity__lte=models.F('low_stock_threshold'),
            stock_quantity__gt=0
        )
        
        for product in low_stock_products:
            self.create_product_alert(
                product=product,
                alert_type='stock_low',
                severity='medium',
                message=f"Low stock: {product.stock_quantity} units remaining (threshold: {product.low_stock_threshold})",
                detected_by='system'
            )
    
    def check_expiry_dates(self):
        """Check product expiry dates"""
        # This would require an expiry_date field in Product model
        # For now, we'll skip this or implement a placeholder
        pass
    
    def process_sensor_alerts(self, sensor_alerts):
        """Process alerts from sensor data"""
        for alert in sensor_alerts:
            self.create_product_alert(
                product=alert['product'],
                alert_type=alert['alert_type'],
                severity=alert['severity'],
                message=alert['message'],
                detected_by='sensor_system'
            )
    
    def create_product_alert(self, product, alert_type, severity, message, detected_by):
        """Create product alert and send notifications"""
        with transaction.atomic():
            # Create alert
            alert = ProductAlert.objects.create(
                product=product,
                alert_type=alert_type,
                severity=severity,
                message=message,
                detected_by=detected_by
            )
            
            # Send notifications
            self.send_role_based_notifications(alert)
    
    def send_role_based_notifications(self, alert):
        """Send notifications based on user roles"""
        # Notify admins for all alerts
        admins = CustomUser.objects.filter(user_type='admin', is_active=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title=f"Product Alert: {alert.get_alert_type_display()}",
                message=f"{alert.message} - Product: {alert.product.name}",
                notification_type='product_alert',
                related_object_type='product_alert',
                related_object_id=alert.id
            )
        
        # Notify product vendor
        if alert.product.vendor:
            Notification.objects.create(
                user=alert.product.vendor,
                title=f"Your Product Alert: {alert.get_alert_type_display()}",
                message=f"{alert.message} - Your product: {alert.product.name}",
                notification_type='product_alert',
                related_object_type='product_alert',
                related_object_id=alert.id
            )
        
        # Notify store managers for critical alerts
        if alert.severity in ['high', 'critical']:
            from django.db.models import Q
            store_managers = CustomUser.objects.filter(
                Q(user_type='admin') | Q(user_type='vendor'),
                is_active=True
            )
            for manager in store_managers:
                if manager != alert.product.vendor:  # Avoid duplicate
                    Notification.objects.create(
                        user=manager,
                        title=f"URGENT: {alert.get_alert_type_display()}",
                        message=f"{alert.message} - Product: {alert.product.name}",
                        notification_type='urgent_alert',
                        related_object_type='product_alert',
                        related_object_id=alert.id
                    )