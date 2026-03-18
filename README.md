# 🚛 Tata Steel Rebar Anti-Theft Monitor Version 2

> AI-Powered Real-Time Cargo Protection System

## 🎯 Problem Statement

Tata Steel faces significant losses from rebar pilferage during transit. This solution provides real-time monitoring with AI-powered detection to prevent theft.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- uv package manager

### Installation

```bash
# Clone and enter project
cd "Tata Problem"

# Create virtual environment
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
uv pip install streamlit pandas plotly folium streamlit-folium pillow numpy

# Run the dashboard
streamlit run app.py
```

### Access Dashboard
### 🌐 Live Deployment

- **Dashboard:** https://build-ids26---tata-steel-hackathon.streamlit.app/
- **User Guide:** https://guide-tata-steel.streamlit.app/
- **Presentation:** https://presentation-tata-steel-hackathon.streamlit.app/

---

## 📖 User Guide

### Dashboard Overview

```
┌─────────────────────────────────────────────────────────┐
│  🚛 Tata Steel Anti-Theft Monitor    [🌙 Night] [🔋87%] │
├─────────────────────────────────────────────────────────┤
│  [48 Active] [23 Trips] [2 Alerts] [1 Theft] [₹45L] [42%]│  ← Quick Stats
├─────────────────────────────────────────────────────────┤
│  [🔴 Theft Demo] [🟢 Normal] [⏮️ Reset] [▶️ Play] [⏹️]  │  ← Controls
├─────────────────────────────────────────────────────────┤
│  🚦 Traffic: 🟢 LIGHT    ⚠️ Route Risk: 🟢 LOW          │  ← Live Status
├─────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────┐        │
│  │   📍 Live Map      │  │   📹 Camera/Alerts │        │
│  │   (Truck Location) │  │   (AI Detection)   │        │
│  └────────────────────┘  └────────────────────┘        │
├─────────────────────────────────────────────────────────┤
│  ⏱️ Timeline [=========>                    ] 45/240    │
├─────────────────────────────────────────────────────────┤
│  [⚖️ Weight Graph]          [⚡ Speed Graph]            │
└─────────────────────────────────────────────────────────┘
```

### Running a Demo

1. **Theft Scenario**
   - Click `🔴 Theft Demo`
   - Click `▶️ Play` for auto-advance OR use the timeline slider
   - Watch the truck stop, weight drop, and camera activate
   - See AI detect persons with bounding boxes

2. **Normal Scenario**
   - Click `🟢 Normal Demo`
   - Observe normal transit operation
   - All indicators stay green

### Understanding Alerts

| Level | Icon | Meaning | Action |
|-------|------|---------|--------|
| L1 | 🟡 | Watchlist | Log only |
| L2 | 🟠 | Warning | SMS driver |
| L3 | 🔴 | Critical | Call + Camera ON |
| L4 | 🚨 | Emergency | Security dispatch |

### Key Features

| Feature | Description |
|---------|-------------|
| 📍 GPS Tracking | Real-time location with geofence alerts |
| ⚖️ Weight Sensors | Instant cargo weight monitoring |
| 📹 AI Camera | Person detection with bounding boxes |
| 🌙 Night Vision | IR mode for 24/7 monitoring |
| 🚦 Traffic Status | Live traffic conditions |
| 📊 Historical Data | Theft statistics and trends |

---

## 🏗️ Project Structure

```
Tata Problem/
├── app.py                 # Main dashboard
├── README.md              # This file
├── requirements.txt       # Dependencies
└── src/
    ├── data/
    │   ├── geofences.py   # Authorized zones
    │   ├── simulator.py   # GPS/weight simulation
    │   └── services.py    # Traffic & historical APIs
    ├── engine/
    │   ├── stop_analyzer.py    # Stop detection
    │   ├── weight_analyzer.py  # Weight monitoring
    │   └── escalation.py       # 4-level SOP alerts
    └── camera/
        ├── simulator.py   # Camera image generation
        └── detector.py    # AI detection
```

---

## ☁️ Deployment

### Streamlit Cloud (Free)

1. Push to GitHub
2. Go to share.streamlit.io
3. Connect your repo
4. Deploy!

### Requirements.txt for deployment
```
streamlit
pandas
plotly
folium
streamlit-folium
pillow
numpy
openpyxl
```

---

## 🎯 Use Cases Covered

✅ **Suspicious Stop Detection** - Alerts when truck stops outside authorized zones  
✅ **Weight Drop Detection** - Detects cargo theft instantly  
✅ **Night Operations** - IR camera mode for 24/7 monitoring  
✅ **Multi-Level SOP** - Escalating response from log → SMS → call → security  
✅ **AI Person Detection** - Identifies unauthorized persons near cargo  
✅ **Traffic Integration** - Route risk assessment  
✅ **Historical Analytics** - Theft trends and recovery stats  

---

## 📞 Support

For questions or issues, contact the development team.

---

*Built for Tata Steel Hackathon 2026*
