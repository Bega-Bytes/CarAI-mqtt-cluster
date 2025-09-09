#!/usr/bin/env python3
import os
import json
import time
import random
import threading
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
from collections import deque, Counter

# # MQTT Configuration
# MQTT_HOST = 'localhost'
# MQTT_PORT = 1883
# MQTT_CLIENT_ID = f'simplified-ai-{random.randint(1000, 9999)}'
# MQTT Configuration
MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_CLIENT_ID = f'simplified-ai-{random.randint(1000, 9999)}'
# AI Configuration
LEARNING_PERIOD = 30  # 30 seconds learning period
RECOMMENDATION_INTERVAL = 20  # Send recommendation every 20 seconds
BREAK_REMINDER_TIME = 200  # Break reminder after 200 seconds
MAX_RECOMMENDATIONS_PER_SESSION = 50

class SimplifiedVehicleAI:
    def __init__(self):
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.setup_mqtt()
        
        # AI State
        self.session_start = None
        self.learning_started = False
        self.learning_complete = False
        self.action_history = deque(maxlen=50)
        self.recommendations_sent = 0
        self.last_recommendation_time = None
        self.break_reminder_sent = False
        
        # Car state tracking
        self.car_state = {
            'climate_on': False,
            'temperature': 22,
            'infotainment_on': False,
            'volume': 50,
            'lights_on': False,
            'brightness': 80,
            'seats_heated': False,
            'seat_position': 5
        }
        
        # Driver preferences (learned from actions)
        self.driver_preferences = {
            'preferred_temperature': 22,
            'preferred_volume': 50,
            'preferred_seat_position': 5,
            'preferred_brightness': 80,
            'likes_music': False,
            'likes_warm_seats': False,
            'common_actions': [],
            'action_sequences': []
        }
        
        # Natural language templates
        self.morning_greetings = [
            "Hello! Based on your preferences,",
            "Hi! I noticed you usually prefer this, so",
            "Hello! From your driving patterns,",
            "Hi again! Your typical routine suggests"
        ]
        
        self.suggestions = {
            'climate_turn_on': [
                "would you like me to turn on the climate control?",
                "should I start the climate system for you?",
                "shall we get the climate going?"
            ],
            'climate_set_temperature': [
                "would you like to set the temperature to {temp}°C?",
                "should I adjust the temperature to your usual {temp}°C?",
                "shall we set it to your preferred {temp}°C?"
            ],
            'infotainment_play': [
                "would you like to listen to some music?",
                "should I start playing your music?",
                "shall we get some tunes going?"
            ],
            'infotainment_set_volume': [
                "would you like to set the volume to {vol}%?",
                "should I adjust the volume to your usual {vol}%?",
                "shall we set the volume to {vol}%?"
            ],
            'lights_turn_on': [
                "would you like me to turn on the ambient lights?",
                "should I turn on the lighting for you?",
                "shall we brighten things up?"
            ],
            'lights_turn_off': [
                "would you like me to turn off the ambient lights?",
                "should I dim the lights for you?",
                "shall we turn off the lighting?"
            ],
            'seats_heat_on': [
                "would you like me to warm up your seat?",
                "should I turn on the seat heating?",
                "shall we get your seat nice and warm?"
            ],
            'seats_adjust': [
                "would you like me to adjust your seat to position {pos}?",
                "should I move your seat to your usual position {pos}?",
                "shall we adjust the seat to your preferred setting?"
            ]
        }
        
        print("🚗🤖 Simplified Vehicle AI Started")
        print(f"Learning Period: {LEARNING_PERIOD} seconds")
        print(f"Break Reminder: After {BREAK_REMINDER_TIME} seconds")
        print("-" * 60)
        
    def setup_mqtt(self):
        """Setup MQTT connections with retry logic"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"Attempting to connect to MQTT broker (attempt {attempt + 1}/{max_retries})")
                self.client.connect(MQTT_HOST, MQTT_PORT, 60)
                self.client.loop_start()
                return
            except Exception as e:
                print(f"❌ MQTT connection failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("❌ Failed to connect after all retries")
                    raise
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to MQTT broker")
            client.subscribe('vehicle/actions')
            print("📡 Subscribed to vehicle/actions")
        else:
            print(f"❌ MQTT connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            data = json.loads(msg.payload.decode())
            
            if topic == 'vehicle/actions':
                self.handle_vehicle_action(data)
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
    
    def handle_vehicle_action(self, action_data):
        """Process vehicle actions and learn preferences"""
        action = action_data.get('action', '')
        timestamp = action_data.get('timestamp', datetime.now().isoformat())
        value = action_data.get('value')
        
        print(f"🚗 Action: {action}{f' ({value})' if value else ''}")
        
        # Add to action history
        self.action_history.append({
            'action': action,
            'timestamp': timestamp,
            'value': value
        })
        
        # Update car state
        self.update_car_state(action, value)
        
        # Start learning if this is the first action
        if not self.learning_started:
            self.start_learning()
        
        # Learn driver preferences
        self.learn_preferences()
    
    def update_car_state(self, action, value):
        """Update car state based on action"""
        if action == 'climate_turn_on':
            self.car_state['climate_on'] = True
        elif action == 'climate_turn_off':
            self.car_state['climate_on'] = False
        elif action == 'climate_set_temperature' and value:
            self.car_state['temperature'] = value
        elif action == 'climate_increase':
            self.car_state['temperature'] = min(self.car_state['temperature'] + 1, 30)
        elif action == 'climate_decrease':
            self.car_state['temperature'] = max(self.car_state['temperature'] - 1, 16)
        elif action == 'infotainment_play':
            self.car_state['infotainment_on'] = True
        elif action == 'infotainment_stop':
            self.car_state['infotainment_on'] = False
        elif action == 'infotainment_set_volume' and value:
            self.car_state['volume'] = value
        elif action == 'infotainment_volume_up':
            self.car_state['volume'] = min(self.car_state['volume'] + 10, 100)
        elif action == 'infotainment_volume_down':
            self.car_state['volume'] = max(self.car_state['volume'] - 10, 0)
        elif action == 'lights_turn_on':
            self.car_state['lights_on'] = True
        elif action == 'lights_turn_off':
            self.car_state['lights_on'] = False
        elif action == 'lights_dim':
            self.car_state['brightness'] = max(self.car_state['brightness'] - 20, 0)
        elif action == 'lights_brighten':
            self.car_state['brightness'] = min(self.car_state['brightness'] + 20, 100)
        elif action == 'seats_heat_on':
            self.car_state['seats_heated'] = True
        elif action == 'seats_heat_off':
            self.car_state['seats_heated'] = False
        elif action == 'seats_adjust' and value:
            self.car_state['seat_position'] = value
    
    def start_learning(self):
        """Start the learning process"""
        self.learning_started = True
        self.session_start = datetime.now()
        
        print(f"🧠 Learning started! Will provide recommendations in {LEARNING_PERIOD} seconds")
        
        # Start learning timer
        threading.Timer(LEARNING_PERIOD, self.complete_learning).start()
        
        # Start break reminder timer
        threading.Timer(BREAK_REMINDER_TIME, self.send_break_reminder).start()
    
    def complete_learning(self):
        """Complete learning phase and start recommendations"""
        self.learning_complete = True
        print("🎓 Learning complete! AI ready to make recommendations")
        
        # Start recommendation loop
        self.start_recommendation_loop()
    
    def start_recommendation_loop(self):
        """Start the recommendation generation loop"""
        def recommendation_loop():
            while (self.learning_complete and 
                   self.recommendations_sent < MAX_RECOMMENDATIONS_PER_SESSION):
                
                # Wait for cooldown
                if self.last_recommendation_time:
                    time_since_last = (datetime.now() - self.last_recommendation_time).total_seconds()
                    if time_since_last < RECOMMENDATION_INTERVAL:
                        time.sleep(RECOMMENDATION_INTERVAL - time_since_last)
                
                # Generate and send recommendation
                recommendations = self.generate_recommendations()
                if recommendations:
                    self.send_recommendations(recommendations)
                    self.recommendations_sent += 1
                    self.last_recommendation_time = datetime.now()
                
                # Wait before next recommendation
                time.sleep(RECOMMENDATION_INTERVAL)
        
        threading.Thread(target=recommendation_loop, daemon=True).start()
    
    def learn_preferences(self):
        """Learn driver preferences from action history"""
        if len(self.action_history) < 3:
            return
        
        actions = [act['action'] for act in self.action_history]
        
        # Learn temperature preference
        temp_actions = [act for act in self.action_history 
                       if act['action'] == 'climate_set_temperature' and act['value']]
        if temp_actions:
            temps = [act['value'] for act in temp_actions]
            self.driver_preferences['preferred_temperature'] = sum(temps) // len(temps)
        
        # Learn volume preference
        vol_actions = [act for act in self.action_history 
                      if act['action'] == 'infotainment_set_volume' and act['value']]
        if vol_actions:
            vols = [act['value'] for act in vol_actions]
            self.driver_preferences['preferred_volume'] = sum(vols) // len(vols)
        
        # Learn seat position preference
        seat_actions = [act for act in self.action_history 
                       if act['action'] == 'seats_adjust' and act['value']]
        if seat_actions:
            positions = [act['value'] for act in seat_actions]
            self.driver_preferences['preferred_seat_position'] = sum(positions) // len(positions)
        
        # Learn behavior patterns
        if 'infotainment_play' in actions:
            self.driver_preferences['likes_music'] = True
        
        if 'seats_heat_on' in actions:
            self.driver_preferences['likes_warm_seats'] = True
        
        # Learn common actions
        action_counts = Counter(actions)
        self.driver_preferences['common_actions'] = [
            action for action, count in action_counts.items() if count >= 2
        ]
    
    def generate_recommendations(self):
        """Generate natural language recommendations"""
        recommendations = []
        recent_actions = [act['action'] for act in list(self.action_history)[-5:]]
        
        # Don't recommend recently performed actions
        recent_action_set = set(recent_actions[-3:])
        
        # Climate recommendations
        if (not self.car_state['climate_on'] and 
            'climate_turn_on' not in recent_action_set):
            
            greeting = random.choice(self.morning_greetings)
            suggestion = random.choice(self.suggestions['climate_turn_on'])
            message = f"{greeting} {suggestion}"
            
            recommendations.append({
                'action': 'climate_turn_on',
                'message': message,
                'value': None
            })
        
        # Temperature adjustment
        if (self.car_state['climate_on'] and 
            self.driver_preferences['preferred_temperature'] != self.car_state['temperature'] and
            'climate_set_temperature' not in recent_action_set):
            
            temp = self.driver_preferences['preferred_temperature']
            greeting = random.choice(self.morning_greetings)
            suggestion = random.choice(self.suggestions['climate_set_temperature']).format(temp=temp)
            message = f"{greeting} {suggestion}"
            
            recommendations.append({
                'action': 'climate_set_temperature',
                'message': message,
                'value': temp
            })
        
        # Music recommendations
        if (not self.car_state['infotainment_on'] and 
            self.driver_preferences['likes_music'] and
            'infotainment_play' not in recent_action_set):
            
            greeting = random.choice(self.morning_greetings)
            suggestion = random.choice(self.suggestions['infotainment_play'])
            message = f"{greeting} {suggestion}"
            
            recommendations.append({
                'action': 'infotainment_play',
                'message': message,
                'value': None
            })
        
        # Volume adjustment
        if (self.car_state['infotainment_on'] and 
            self.driver_preferences['preferred_volume'] != self.car_state['volume'] and
            'infotainment_set_volume' not in recent_action_set):
            
            vol = self.driver_preferences['preferred_volume']
            greeting = random.choice(self.morning_greetings)
            suggestion = random.choice(self.suggestions['infotainment_set_volume']).format(vol=vol)
            message = f"{greeting} {suggestion}"
            
            recommendations.append({
                'action': 'infotainment_set_volume',
                'message': message,
                'value': vol
            })
        
        # Lighting recommendations (time-based)
        current_hour = datetime.now().hour
        if current_hour >= 18 or current_hour <= 6:  # Evening/night
            if (not self.car_state['lights_on'] and 
                'lights_turn_on' not in recent_action_set):
                
                message = "It's getting dark, would you like me to turn on the ambient lights for a cozy atmosphere?"
                recommendations.append({
                    'action': 'lights_turn_on',
                    'message': message,
                    'value': None
                })
        else:  # Day time
            if (self.car_state['lights_on'] and 
                'lights_turn_off' not in recent_action_set):
                
                message = "It's bright outside, would you like me to turn off the ambient lights to save energy?"
                recommendations.append({
                    'action': 'lights_turn_off',
                    'message': message,
                    'value': None
                })
        
        # Seat heating recommendations
        if (not self.car_state['seats_heated'] and 
            self.driver_preferences['likes_warm_seats'] and
            'seats_heat_on' not in recent_action_set):
            
            greeting = random.choice(self.morning_greetings)
            suggestion = random.choice(self.suggestions['seats_heat_on'])
            message = f"{greeting} {suggestion}"
            
            recommendations.append({
                'action': 'seats_heat_on',
                'message': message,
                'value': None
            })
        
        # Seat position adjustment
        if (self.driver_preferences['preferred_seat_position'] != self.car_state['seat_position'] and
            'seats_adjust' not in recent_action_set):
            
            pos = self.driver_preferences['preferred_seat_position']
            greeting = random.choice(self.morning_greetings)
            suggestion = random.choice(self.suggestions['seats_adjust']).format(pos=pos)
            message = f"{greeting} {suggestion}"
            
            recommendations.append({
                'action': 'seats_adjust',
                'message': message,
                'value': pos
            })
        
        # Return top 2 recommendations
        return recommendations[:2] if recommendations else None
    
    def send_break_reminder(self):
        """Send break reminder after 200, 600, 1000 seconds"""
        if not self.break_reminder_sent:
            self.break_reminder_sent = True
            
            break_messages = [
                "You've been driving for a while now. Would you like to take a break? Your safety is important!",
                "Time for a quick break! You've been on the road for over 3 minutes. Shall we find a rest stop?",
                "Hey there! Consider taking a short break - you've been driving for quite some time now.",
                "Safety first! You've been driving continuously. Would you like to take a breather?"
            ]
            
            message = random.choice(break_messages)
            
            recommendation_data = {
                'type': 'ai_suggestion',
                'recommendations': [{
                    'action': 'take_break',
                    'message': message,
                    'value': None
                }],
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                self.client.publish('vehicle/recommendations', json.dumps(recommendation_data))
                print(f"\n🛑 BREAK REMINDER SENT:")
                print(f"   • {message}")
                print("-" * 60)
            except Exception as e:
                print(f"❌ Error sending break reminder: {e}")
    
    def send_recommendations(self, recommendations):
        """Send recommendations via MQTT"""
        if not recommendations:
            return
        
        recommendation_data = {
            'type': 'ai_suggestion',
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            message = json.dumps(recommendation_data)
            self.client.publish('vehicle/recommendations', message)
            
            print(f"\n🤖 RECOMMENDATION SENT #{self.recommendations_sent + 1}:")
            for rec in recommendations:
                print(f"   • {rec['message']}")
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ Error sending recommendation: {e}")
    
    def get_session_duration(self):
        """Get session duration in seconds"""
        if not self.session_start:
            return 0
        return int((datetime.now() - self.session_start).total_seconds())
    
    def run(self):
        """Run the AI system"""
        print("🚀 Simplified AI System running...")
        print("Use the dashboard to interact with the vehicle")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
                
                # Print status every 30 seconds
                if self.session_start and self.get_session_duration() % 30 == 0:
                    duration = self.get_session_duration()
                    actions = len(self.action_history)
                    phase = "Ready" if self.learning_complete else ("Learning" if self.learning_started else "Waiting")
                    print(f"📊 Status: {phase} | Duration: {duration}s | Actions: {actions} | Recommendations: {self.recommendations_sent}")
                    
        except KeyboardInterrupt:
            print(f"\n🛑 AI System stopped")
            print(f"Session Summary:")
            print(f"  • Duration: {self.get_session_duration()}s")
            print(f"  • Actions processed: {len(self.action_history)}")
            print(f"  • Recommendations sent: {self.recommendations_sent}")
            print(f"  • Learned preferences: {len([k for k, v in self.driver_preferences.items() if v and k != 'common_actions'])}")
        
        finally:
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    print("🚀 Starting Simplified Vehicle AI...")
    print(f"MQTT Host: {MQTT_HOST}")
    print(f"MQTT Port: {MQTT_PORT}")
    print("=" * 50)
    
    try:
        ai_system = SimplifiedVehicleAI()
        ai_system.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise