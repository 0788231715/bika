import pandas as pd
from bika.models import ProductDataset, TrainedModel
import numpy as np
import json
from datetime import datetime, timedelta
import os
from django.conf import settings

try:
    from sklearn.ensemble import IsolationForest, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("scikit-learn not available. Using simplified AI service.")

class RealProductAIService:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        if SKLEARN_AVAILABLE:
            self.load_trained_models()
        else:
            print("AI Service running in simplified mode (scikit-learn not available)")
    
    def load_trained_models(self):
        """Load pre-trained models from database"""
        if not SKLEARN_AVAILABLE:
            return
            
        try:
            active_models = TrainedModel.objects.filter(is_active=True)
            for model_obj in active_models:
                model_path = os.path.join(settings.MEDIA_ROOT, str(model_obj.model_file))
                if os.path.exists(model_path):
                    self.models[model_obj.model_type] = joblib.load(model_path)
                    print(f"Loaded model: {model_obj.model_type}")
        except Exception as e:
            print(f"Error loading models: {e}")
    
    def train_anomaly_detection_model(self, dataset_id):
        """Train anomaly detection model on real dataset"""
        if not SKLEARN_AVAILABLE:
            print("scikit-learn not available. Cannot train models.")
            return None
            
        try:
            dataset = ProductDataset.objects.get(id=dataset_id, dataset_type='anomaly_detection')
            dataset_path = os.path.join(settings.MEDIA_ROOT, str(dataset.data_file))
            
            # Load real dataset
            df = pd.read_csv(dataset_path)
            
            # Prepare features (adjust based on your dataset columns)
            feature_columns = ['stock_quantity', 'sales_velocity', 'return_rate', 
                             'defect_rate', 'shelf_life_days']
            
            # Use only existing columns
            available_features = [col for col in feature_columns if col in df.columns]
            X = df[available_features]
            
            # Handle missing values
            X = X.fillna(X.mean())
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train model
            model = IsolationForest(
                n_estimators=100,
                contamination=0.1,
                random_state=42
            )
            model.fit(X_scaled)
            
            # Save model
            model_filename = f"anomaly_model_{dataset_id}_{datetime.now().strftime('%Y%m%d')}.pkl"
            model_path = os.path.join(settings.MEDIA_ROOT, 'trained_models', model_filename)
            joblib.dump(model, model_path)
            
            # Save to database
            trained_model = TrainedModel.objects.create(
                name=f"Anomaly Detection Model - {dataset.name}",
                model_type='anomaly_detection',
                dataset=dataset,
                model_file=f'trained_models/{model_filename}',
                feature_columns=available_features
            )
            
            self.models['anomaly_detection'] = model
            self.scalers['anomaly_detection'] = scaler
            
            return trained_model
            
        except Exception as e:
            print(f"Error training model: {e}")
            return None
    
    def detect_product_anomalies(self, product_data):
        """Detect anomalies in real product data"""
        if not SKLEARN_AVAILABLE:
            # Simplified anomaly detection without scikit-learn
            anomalies = []
            for product in product_data:
                # Simple rule-based anomaly detection
                if (hasattr(product, 'stock_quantity') and 
                    product.stock_quantity > 0 and 
                    product.stock_quantity <= getattr(product, 'low_stock_threshold', 5)):
                    anomalies.append({
                        'product_id': product.id,
                        'anomaly_score': 0.8,
                        'features': {'stock_quantity': product.stock_quantity},
                        'reason': 'Low stock detected'
                    })
            return anomalies
        
        if 'anomaly_detection' not in self.models:
            return []
        
        try:
            # Convert product data to features
            features = []
            product_ids = []
            
            for product in product_data:
                feature_vector = []
                for feature in self.scalers['anomaly_detection'].feature_names_in_:
                    feature_vector.append(getattr(product, feature, 0))
                features.append(feature_vector)
                product_ids.append(product.id)
            
            # Scale features
            features_scaled = self.scalers['anomaly_detection'].transform(features)
            
            # Predict anomalies
            predictions = self.models['anomaly_detection'].predict(features_scaled)
            anomaly_scores = self.models['anomaly_detection'].decision_function(features_scaled)
            
            # Return anomalies
            anomalies = []
            for i, (pred, score) in enumerate(zip(predictions, anomaly_scores)):
                if pred == -1:  # Anomaly detected
                    anomalies.append({
                        'product_id': product_ids[i],
                        'anomaly_score': score,
                        'features': dict(zip(self.scalers['anomaly_detection'].feature_names_in_, features[i]))
                    })
            
            return anomalies
            
        except Exception as e:
            print(f"Error detecting anomalies: {e}")
            return []
    
    def analyze_sensor_data(self, sensor_readings):
        """Analyze real sensor data for quality issues"""
        alerts = []
        
        for reading in sensor_readings:
            # Define normal ranges based on product type
            normal_ranges = self.get_normal_ranges(reading.product)
            
            if reading.sensor_type in normal_ranges:
                min_val, max_val = normal_ranges[reading.sensor_type]
                
                if reading.value < min_val or reading.value > max_val:
                    alert_type = self.determine_alert_type(reading.sensor_type, reading.value, min_val, max_val)
                    severity = self.determine_severity(reading.sensor_type, reading.value, min_val, max_val)
                    
                    alerts.append({
                        'product': reading.product,
                        'sensor_type': reading.sensor_type,
                        'value': reading.value,
                        'normal_range': f"{min_val}-{max_val}",
                        'alert_type': alert_type,
                        'severity': severity,
                        'message': self.generate_alert_message(reading, alert_type, severity)
                    })
        
        return alerts
    
    def get_normal_ranges(self, product):
        """Get normal sensor ranges for specific product type"""
        # Define based on your product categories
        ranges = {
            'temperature': (15, 25),  # Celsius
            'humidity': (30, 70),     # Percentage
            'weight': (0.95, 1.05),   # Ratio to expected
            'vibration': (0, 5),      # Intensity
            'pressure': (95, 105),    # kPa
        }
        
        # Adjust ranges based on product category
        if hasattr(product, 'category') and product.category:
            category_name = product.category.name.lower()
            if 'food' in category_name:
                ranges['temperature'] = (0, 5)  # Refrigerated
            elif 'electronic' in category_name:
                ranges['humidity'] = (20, 50)   # Lower humidity
            elif 'fragile' in category_name:
                ranges['vibration'] = (0, 2)    # Lower vibration tolerance
        
        return ranges
    
    def determine_alert_type(self, sensor_type, value, min_val, max_val):
        """Determine the type of alert based on sensor reading"""
        alert_types = {
            'temperature': 'temperature_anomaly',
            'humidity': 'humidity_issue',
            'weight': 'weight_discrepancy',
            'vibration': 'vibration_alert',
            'pressure': 'pressure_anomaly'
        }
        return alert_types.get(sensor_type, 'sensor_anomaly')
    
    def determine_severity(self, sensor_type, value, min_val, max_val):
        """Determine severity based on deviation from normal range"""
        range_width = max_val - min_val
        deviation = min(abs(value - min_val), abs(value - max_val))
        
        if deviation > range_width * 0.5:
            return 'critical'
        elif deviation > range_width * 0.3:
            return 'high'
        elif deviation > range_width * 0.1:
            return 'medium'
        else:
            return 'low'
    
    def generate_alert_message(self, reading, alert_type, severity):
        """Generate descriptive alert message"""
        messages = {
            'temperature_anomaly': f"Temperature anomaly detected: {reading.value}°C",
            'humidity_issue': f"Humidity issue: {reading.value}%",
            'weight_discrepancy': f"Weight discrepancy: {reading.value}",
            'vibration_alert': f"Unusual vibration detected: {reading.value}",
            'pressure_anomaly': f"Pressure anomaly: {reading.value}"
        }
        
        base_message = messages.get(alert_type, f"Sensor anomaly: {reading.sensor_type} = {reading.value}")
        return f"{severity.upper()} - {base_message}"