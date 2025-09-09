# Conversational Vehicle AI with MQTT Communication

This project implements an intelligent vehicle assistant that learns driver behavior patterns and provides natural language recommendations for non-driving vehicle features. The system uses MQTT messaging for real-time communication between components and employs machine learning trained on synthetic driving data.

## System Overview

The AI assistant monitors driver interactions with vehicle controls (climate, infotainment, lighting, seats) and learns individual preferences over time. After a brief learning period, it proactively suggests actions using conversational language like:

- "Good morning! Based on your preferences, would you like me to turn on the climate control?"
- "It's getting dark, shall we turn on the ambient lights for a cozy atmosphere?"

## Core Components

**AI Recommendation Engine**  
A pattern recognition system that analyzes driver behavior to learn preferences such as preferred temperature settings, music habits, seat positions, and comfort patterns. The AI generates contextually-aware suggestions with confidence scoring and natural language explanations.

**Web Dashboard**  
Real-time interface providing vehicle controls and displaying AI recommendations with accept/dismiss functionality. Shows current vehicle state, action history, and learning progress for testing.

**MQTT Communication Layer**  
Handles message routing between the dashboard, AI engine, and vehicle systems using publish/subscribe patterns for decoupled, scalable communication.

## Why MQTT?

MQTT was selected as the communication protocol for several technical reasons:

- **Low Latency**: Sub-millisecond message delivery ensures real-time responsiveness for vehicle interactions
- **Lightweight Protocol**: Minimal bandwidth usage suitable for embedded vehicle systems
- **Publish/Subscribe Architecture**: Enables loose coupling between components, allowing the AI engine, dashboard, and vehicle systems to operate independently
- **Quality of Service**: Guarantees message delivery reliability for critical vehicle commands
- **Scalability**: Easy to add new vehicle systems or AI components without modifying existing code
- **Standardization**: Industry-standard protocol widely supported in IoT and automotive applications

## Technical Architecture

The system operates on a distributed microservices architecture deployed in Kubernetes. The MQTT broker (Eclipse Mosquitto) serves as the central message hub, while the AI engine processes driver actions to generate recommendations. The web dashboard provides both manual vehicle control and AI interaction capabilities.

**Training Data**  
The AI model was trained using synthetically generated driver behavior data created through OpenAI's API, producing realistic driving patterns across different driver personalities, trip contexts and vehicle usage scenarios.

**Learning Process**  
The system begins with a 30-second observation period, then starts making recommendations every 20 seconds. It tracks patterns like temperature preferences, music usage, seat heating habits, and contextual behaviors (time-based lighting preferences).

## Business Value

This system demonstrates practical applications for automotive AI assistants, focusing on:

- **Driver Safety**: Reducing manual interactions with vehicle controls while driving
- **Personalization**: Learning individual preferences rather than using generic presets  
- **User Experience**: Natural language interactions instead of complex menu navigation
- **Efficiency**: Proactive suggestions reduce time spent adjusting vehicle settings

The architecture supports integration with existing vehicle CAN bus systems and OEM platforms while maintaining safety constraints and user privacy.

---

## Repo layout

```text
.
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── mosquitto.conf
├── matrix_publisher.py
├── html.html
├── k8s-mqtt.yaml                 # Kubernetes manifests (broker + AI)
└── ml/                           # Optional ML/aux scripts & data
    ├── dataset_generator.py
    ├── recommendation_engine.py
    ├── recommendation_api.py
    ├── vehicle_ai_training_data.csv
    └── vehicle_recommendation_model.pkl
```

---

## Quick Start — Docker Compose

### Prerequisites

- Docker Desktop **or** Rancher Desktop (with Docker engine enabled)
- `docker compose` plugin

### 1) Clone

```bash
git clone https://github.com/Bega-Bytes/CarAI-mqtt-cluster.git
cd CarAI-mqtt-cluster
```

### 2) Start everything

> Build images (if needed) and start broker + AI.

```bash
docker compose up -d --build
```

This launches:

- **mosquitto-broker** → ports **1883** (MQTT/TCP), **9001** (MQTT/WebSockets)  
- **matrix-publisher** → connects to `mosquitto:1883` via Docker DNS

### 3) Open the dashboard

Serve the dashboard file locally and connect it to the broker:

```bash
# from repo root
python -m http.server 8080
# then open in your browser:
# http://localhost:8080/html.html
```

On the dashboard page:

- **Host:** `localhost`  
- **Port:** `9001`  
- Click **Connect** → you should see “connected”.

Now interact with the UI (toggle climate, etc.).  
The AI publishes suggestions on `vehicle/recommendations`.

### 4) Verify quickly (optional)

```bash
# broker logs
docker logs -f mosquitto-broker

# subscribe to all topics from inside the broker container
docker exec -it mosquitto-broker   mosquitto_sub -h 127.0.0.1 -p 1883 -t '#' -v
```

### 5) Useful lifecycle commands

```bash
# bring up only the broker
docker compose up -d --build mosquitto

# bring up only the AI
docker compose up -d --build matrix-publisher

# see containers
docker ps

# tail logs
docker logs -f mosquitto-broker
docker logs -f matrix-publisher

# stop & remove everything (including volumes)
docker compose down -v
```

---

## Rancher Desktop (Kubernetes) — Deploy & Check

Use this to run the same workloads (broker + AI) as **Deployments/Services** in Rancher Desktop.

### Prerequisites

- Rancher Desktop installed, **Kubernetes enabled**
- `kubectl` configured with context `rancher-desktop`

Verify:

```bash
kubectl config current-context
# should print: rancher-desktop
```

### 1) Apply the manifest

```bash
# from repo root
kubectl apply -f k8s-mqtt.yaml
```

> If you build/publish your own AI image, change the `image:` in the Deployment or push to a registry everyone can pull from.

### 2) Inspect via CLI

```bash
kubectl get deploy,po,svc
kubectl logs deploy/matrix-publisher
```

**Expected:**

- A **Deployment** and **Service** for **Mosquitto** (ports **1883** & **9001**)
- A **Deployment** for **matrix-publisher** (reads `MQTT_HOST=mosquitto`, `MQTT_PORT=1883`)

### 3) Make MQTT reachable from the local browser

```bash
# forward broker ports to your laptop
kubectl port-forward svc/mosquitto 1883:1883 9001:9001
```

Now open `html.html` locally (as in the Compose section), connect to **Host** `localhost`, **Port** `9001`.

### 4) Verify in Rancher Desktop UI

- Open **Rancher Desktop** ➜ **Kubernetes**.
- **Workloads ➜ Deployments:** see `mosquitto` and `matrix-publisher`.
- Click a workload ➜ **Logs** to watch activity.
- **Services:** confirm `mosquitto` exposes ports **1883** and **9001**.
