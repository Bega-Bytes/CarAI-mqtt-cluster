import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import pickle
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class VehicleRecommendationEngine:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.label_encoders = {}
        self.driver_patterns = defaultdict(list)
        self.driver_sequences = defaultdict(list)
        self.is_trained = False
        
    def prepare_features(self, df):
        """Prepare features for training"""
        # Create categorical encoders
        categorical_cols = ['weather', 'trip_type', 'time_of_day']
        
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df[col])
            else:
                df[f'{col}_encoded'] = self.label_encoders[col].transform(df[col])
        
        # Create time-based features
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        # Create sequence features (last 2 actions)
        sequence_features = []
        for driver_id in df['driver_id'].unique():
            driver_data = df[df['driver_id'] == driver_id].sort_values('timestamp')
            
            for i, row in driver_data.iterrows():
                recent_actions = list(driver_data[driver_data.index < i]['action'].tail(2))
                
                # Pad with 'none' if less than 2 previous actions
                while len(recent_actions) < 2:
                    recent_actions.insert(0, 'none')
                
                sequence_features.append({
                    'index': i,
                    'prev_action_1': recent_actions[-1] if len(recent_actions) > 0 else 'none',
                    'prev_action_2': recent_actions[-2] if len(recent_actions) > 1 else 'none'
                })
        
        seq_df = pd.DataFrame(sequence_features).set_index('index')
        df = df.join(seq_df)
        
        return df
    
    def extract_driver_patterns(self, df):
        """Extract common patterns for each driver"""
        for driver_id in df['driver_id'].unique():
            driver_data = df[df['driver_id'] == driver_id]
            
            # Pattern 1: Action frequency by context
            context_patterns = []
            for _, row in driver_data.iterrows():
                context = {
                    'weather': row['weather'],
                    'trip_type': row['trip_type'],
                    'time_of_day': row['time_of_day'],
                    'outside_temperature': row['outside_temperature'],
                    'action': row['action']
                }
                context_patterns.append(context)
            
            self.driver_patterns[driver_id] = context_patterns
            
            # Pattern 2: Action sequences
            sequences = driver_data.groupby('trip_id')['action'].apply(list).tolist()
            self.driver_sequences[driver_id] = sequences
    
    def train(self, csv_file_path):
        """Train the recommendation model"""
        print("Loading dataset...")
        df = pd.read_csv(csv_file_path)
        
        print("Preparing features...")
        df = self.prepare_features(df)
        
        print("Extracting driver patterns...")
        self.extract_driver_patterns(df)
        
        # Prepare training data
        feature_cols = [
            'driver_id', 'weather_encoded', 'trip_type_encoded', 'time_of_day_encoded',
            'outside_temperature', 'passenger_count', 'is_weekend', 'hour', 'day_of_week'
        ]
        
        # Add previous actions as features
        prev_action_encoder = LabelEncoder()
        all_actions = list(df['action'].unique()) + ['none']
        prev_action_encoder.fit(all_actions)
        self.label_encoders['prev_actions'] = prev_action_encoder
        
        df['prev_action_1_encoded'] = prev_action_encoder.transform(df['prev_action_1'])
        df['prev_action_2_encoded'] = prev_action_encoder.transform(df['prev_action_2'])
        
        feature_cols.extend(['prev_action_1_encoded', 'prev_action_2_encoded'])
        
        # Prepare target
        target_encoder = LabelEncoder()
        df['action_encoded'] = target_encoder.fit_transform(df['action'])
        self.label_encoders['action'] = target_encoder
        
        # Split data
        X = df[feature_cols].fillna(0)
        y = df['action_encoded']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        print("Training model...")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"Training accuracy: {train_score:.3f}")
        print(f"Test accuracy: {test_score:.3f}")
        
        self.is_trained = True
        print("Model training completed!")
        
        return {"train_accuracy": train_score, "test_accuracy": test_score}
    
    def get_recommendations(self, driver_id, current_context, recent_actions=None):
        """Get recommendations for a driver given current context"""
        if not self.is_trained:
            return {"error": "Model not trained yet"}
        
        if recent_actions is None:
            recent_actions = []
        
        # Pad recent actions
        padded_actions = ['none', 'none'] + recent_actions
        prev_action_1 = padded_actions[-1]
        prev_action_2 = padded_actions[-2]
        
        # Prepare input features
        try:
            features = [
                driver_id,
                self.label_encoders['weather'].transform([current_context['weather']])[0],
                self.label_encoders['trip_type'].transform([current_context['trip_type']])[0],
                self.label_encoders['time_of_day'].transform([current_context['time_of_day']])[0],
                current_context['outside_temperature'],
                current_context.get('passenger_count', 1),
                current_context.get('is_weekend', False),
                current_context.get('hour', 12),
                current_context.get('day_of_week', 0),
                self.label_encoders['prev_actions'].transform([prev_action_1])[0],
                self.label_encoders['prev_actions'].transform([prev_action_2])[0]
            ]
        except KeyError as e:
            return {"error": f"Unknown context value: {e}"}
        
        # Get prediction probabilities
        X = np.array(features).reshape(1, -1)
        probabilities = self.model.predict_proba(X)[0]
        
        # Get top 3 recommendations
        top_indices = np.argsort(probabilities)[-3:][::-1]
        recommendations = []
        
        for idx in top_indices:
            action = self.label_encoders['action'].inverse_transform([idx])[0]
            confidence = probabilities[idx]
            
            if confidence > 0.1:  # Only recommend if confidence > 10%
                reason = self._explain_recommendation(driver_id, action, current_context)
                recommendations.append({
                    'action': action,
                    'confidence': float(confidence),
                    'reason': reason
                })
        
        return {
            'recommendations': recommendations,
            'driver_id': driver_id,
            'context': current_context
        }
    
    def _explain_recommendation(self, driver_id, action, context):
        """Generate human-readable explanation for recommendation"""
        explanations = {
            'climate_turn_on': f"You usually turn on climate when it's {context['weather']} weather",
            'seats_heat_on': f"You typically use seat heating when temperature is {context['outside_temperature']}°C",
            'infotainment_play': f"You usually play music during {context['trip_type']} trips",
            'lights_turn_on': f"You often turn on lights during {context['time_of_day']} drives"
        }
        
        return explanations.get(action, f"Based on your {context['trip_type']} driving patterns")
    
    def save_model(self, filepath):
        """Save the trained model and encoders"""
        model_data = {
            'model': self.model,
            'label_encoders': self.label_encoders,
            'driver_patterns': dict(self.driver_patterns),
            'driver_sequences': dict(self.driver_sequences),
            'is_trained': self.is_trained
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath):
        """Load a trained model"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.label_encoders = model_data['label_encoders']
        self.driver_patterns = defaultdict(list, model_data['driver_patterns'])
        self.driver_sequences = defaultdict(list, model_data['driver_sequences'])
        self.is_trained = model_data['is_trained']
        
        print(f"Model loaded from {filepath}")

# Usage example
if __name__ == "__main__":
    # Initialize and train the model
    engine = VehicleRecommendationEngine()
    
    # Train on your generated dataset
    results = engine.train('vehicle_ai_training_data.csv')
    
    # Save the trained model
    engine.save_model('vehicle_recommendation_model.pkl')
    
    # Test recommendations
    test_context = {
        'weather': 'cold',
        'trip_type': 'commute_work',
        'time_of_day': 'morning',
        'outside_temperature': 2,
        'passenger_count': 1,
        'is_weekend': False,
        'hour': 8,
        'day_of_week': 1
    }
    
    recommendations = engine.get_recommendations(
        driver_id=0,
        current_context=test_context,
        recent_actions=['climate_turn_on']
    )
    
    print("\nTest Recommendations:")
    print(json.dumps(recommendations, indent=2))
