import openai
import json
import pandas as pd
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os

class VehicleAIDatasetGenerator:
    def __init__(self, api_key: str):
        """Initialize the dataset generator with OpenAI API key"""
        openai.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)
        
        # Define available actions matching your MQTT topics
        self.actions = [
            "climate_turn_on", "climate_turn_off", "climate_set_temperature",
            "climate_increase", "climate_decrease", "infotainment_play",
            "infotainment_stop", "infotainment_volume_up", "infotainment_volume_down",
            "infotainment_set_volume", "lights_turn_on", "lights_turn_off",
            "lights_dim", "lights_brighten", "seats_heat_on", "seats_heat_off",
            "seats_adjust"
        ]
        
        # Define context variables
        self.weather_conditions = ["sunny", "rainy", "snowy", "cloudy", "foggy"]
        self.trip_types = ["commute_work", "commute_home", "leisure", "shopping", "long_trip"]
        self.times_of_day = ["morning", "afternoon", "evening", "night"]
        
    def generate_driver_persona(self) -> Dict[str, Any]:
        """Generate a realistic driver persona using OpenAI"""
        prompt = """Generate a realistic driver persona for a car AI system. Include:
        - Age range and demographic
        - Driving habits and preferences
        - Climate preferences (temperature range, fan usage)
        - Infotainment preferences (music, volume levels)
        - Lighting preferences
        - Seat preferences
        - Common trip patterns
        - Personality traits that affect car usage
        
        Return as JSON format with clear categories."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            
            persona_text = response.choices[0].message.content
            # Try to parse as JSON, if not possible, create structured data
            try:
                return json.loads(persona_text)
            except:
                return {"description": persona_text, "type": "descriptive"}
                
        except Exception as e:
            print(f"Error generating persona: {e}")
            return self.create_default_persona()
    
    def create_default_persona(self) -> Dict[str, Any]:
        """Create a default persona if API call fails"""
        personas = [
            {
                "age_range": "25-35",
                "type": "tech_savvy_commuter",
                "climate_preference": {"temp_range": [21, 23], "fan_usage": "auto"},
                "infotainment": {"music_type": "streaming", "volume_range": [15, 25]},
                "lighting": {"preference": "auto_adjust", "brightness": "medium"},
                "personality": ["efficient", "routine-oriented", "tech-friendly"]
            },
            {
                "age_range": "35-50",
                "type": "family_driver",
                "climate_preference": {"temp_range": [20, 22], "fan_usage": "manual"},
                "infotainment": {"music_type": "radio", "volume_range": [10, 20]},
                "lighting": {"preference": "manual", "brightness": "low"},
                "personality": ["cautious", "comfort-focused", "routine-based"]
            }
        ]
        return random.choice(personas)
    
    def generate_behavior_sequence(self, persona: Dict, context: Dict) -> List[Dict]:
        """Generate a realistic sequence of driver actions"""
        prompt = f"""
        Based on this driver persona: {json.dumps(persona)}
        And this trip context: {json.dumps(context)}
        
        Generate a realistic sequence of 5-15 car actions that this driver would perform.
        Use these exact action names: {', '.join(self.actions)}
        
        Consider:
        - Logical action sequences (e.g., turning on climate before adjusting temperature)
        - Driver habits and preferences
        - Trip context (weather, time, destination)
        - Realistic timing between actions
        
        Return as JSON array with objects containing:
        - action: the exact action name
        - timestamp_offset: seconds from trip start
        - context_reason: why this action makes sense
        - value: any specific value (temperature, volume, etc.)
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            sequence_text = response.choices[0].message.content
            # Extract JSON from response
            start_idx = sequence_text.find('[')
            end_idx = sequence_text.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                json_text = sequence_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                return self.create_default_sequence()
                
        except Exception as e:
            print(f"Error generating sequence: {e}")
            return self.create_default_sequence()
    
    def create_default_sequence(self) -> List[Dict]:
        """Create a default action sequence"""
        sequences = [
            [
                {"action": "climate_turn_on", "timestamp_offset": 10, "context_reason": "Starting car", "value": None},
                {"action": "climate_set_temperature", "timestamp_offset": 15, "context_reason": "Setting comfort temperature", "value": 22},
                {"action": "infotainment_play", "timestamp_offset": 30, "context_reason": "Starting music", "value": None},
                {"action": "infotainment_set_volume", "timestamp_offset": 35, "context_reason": "Adjusting volume", "value": 18}
            ],
            [
                {"action": "lights_turn_on", "timestamp_offset": 5, "context_reason": "Dark conditions", "value": None},
                {"action": "seats_heat_on", "timestamp_offset": 20, "context_reason": "Cold weather", "value": None},
                {"action": "climate_turn_on", "timestamp_offset": 25, "context_reason": "Defrosting", "value": None}
            ]
        ]
        return random.choice(sequences)
    
    def generate_trip_context(self) -> Dict[str, Any]:
        """Generate random trip context"""
        return {
            "weather": random.choice(self.weather_conditions),
            "trip_type": random.choice(self.trip_types),
            "time_of_day": random.choice(self.times_of_day),
            "outside_temperature": random.randint(-10, 35),
            "trip_duration_minutes": random.randint(5, 120),
            "passenger_count": random.randint(1, 4),
            "is_weekend": random.choice([True, False])
        }
    
    def generate_dataset(self, num_drivers: int = 50, trips_per_driver: int = 20) -> pd.DataFrame:
        """Generate complete dataset"""
        print(f"Generating dataset with {num_drivers} drivers and {trips_per_driver} trips each...")
        
        dataset = []
        
        for driver_id in range(num_drivers):
            print(f"Generating data for driver {driver_id + 1}/{num_drivers}")
            
            # Generate driver persona
            persona = self.generate_driver_persona()
            
            for trip_id in range(trips_per_driver):
                # Generate trip context
                context = self.generate_trip_context()
                
                # Generate behavior sequence
                actions = self.generate_behavior_sequence(persona, context)
                
                # Create base timestamp
                base_time = datetime.now() - timedelta(days=random.randint(0, 365))
                
                # Add each action to dataset
                for action_data in actions:
                    record = {
                        'driver_id': driver_id,
                        'trip_id': f"{driver_id}_{trip_id}",
                        'timestamp': base_time + timedelta(seconds=action_data.get('timestamp_offset', 0)),
                        'action': action_data['action'],
                        'value': action_data.get('value'),
                        'context_reason': action_data.get('context_reason', ''),
                        'weather': context['weather'],
                        'trip_type': context['trip_type'],
                        'time_of_day': context['time_of_day'],
                        'outside_temperature': context['outside_temperature'],
                        'trip_duration_minutes': context['trip_duration_minutes'],
                        'passenger_count': context['passenger_count'],
                        'is_weekend': context['is_weekend'],
                        'driver_persona': json.dumps(persona)
                    }
                    dataset.append(record)
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
        
        return pd.DataFrame(dataset)
    
    def save_dataset(self, df: pd.DataFrame, filename: str = "vehicle_ai_dataset.csv"):
        """Save dataset to CSV"""
        df.to_csv(filename, index=False)
        print(f"Dataset saved to {filename}")
        print(f"Total records: {len(df)}")
        print(f"Unique drivers: {df['driver_id'].nunique()}")
        print(f"Unique trips: {df['trip_id'].nunique()}")
        print(f"Action distribution:\n{df['action'].value_counts()}")

# Usage example
if __name__ == "__main__":
    # Set your OpenAI API key
    API_KEY = "your_openai_api_key_here"  # Replace with your actual API key
    
    # Initialize generator
    generator = VehicleAIDatasetGenerator(API_KEY)
    
    # Generate dataset
    # Start small for testing, then increase
    dataset = generator.generate_dataset(num_drivers=10, trips_per_driver=5)
    
    # Save dataset
    generator.save_dataset(dataset, "vehicle_ai_training_dataset.csv")
    
    # Display sample data
    print("\nSample data:")
    print(dataset.head(10))
    
    print("\nDataset shape:", dataset.shape)
    print("\nColumns:", list(dataset.columns))
