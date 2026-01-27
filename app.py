"""
Tata Steel Rebar Pilferage Prevention Dashboard
Enhanced with more visualizations and interactivity
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data.simulator import TransitSimulator
from src.data.geofences import AUTHORIZED_ZONES, is_in_authorized_zone
from src.data.services import traffic_service, historical_service
from src.engine.stop_analyzer import StopAnalyzer
from src.engine.weight_analyzer import EnhancedWeightAnalyzer
from src.engine.escalation import EscalationEngine, AlertLevel
from src.camera.simulator import EnhancedCameraSimulator, is_night_time
from src.camera.detector import SimpleAIDetector

# Page config
st.set_page_config(
    page_title="Tata Steel - Anti-Theft Monitor",
    page_icon="🚛",
    layout="wide"
)

# Enhanced CSS
st.markdown("""
<style>
    .main-header { font-size: 2rem; color: #1a5276; font-weight: 700; margin: 0; }
    .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 color: white; padding: 1rem; border-radius: 12px; text-align: center; 
                 box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .stat-card-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .stat-card-orange { background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%); }
    .stat-card-red { background: linear-gradient(135deg, #cb2d3e 0%, #ef473a 100%); }
    .stat-card-blue { background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%); }
    .stat-number { font-size: 2rem; font-weight: bold; }
    .stat-label { font-size: 0.8rem; opacity: 0.9; margin-top: 0.3rem; }
    .alert-banner { padding: 1rem 1.5rem; border-radius: 10px; margin: 0.5rem 0; 
                    display: flex; align-items: center; }
    .alert-critical { background: linear-gradient(135deg, #e74c3c, #c0392b); color: white; }
    .alert-normal { background: linear-gradient(135deg, #27ae60, #2ecc71); color: white; }
    .info-card { background: #f8f9fa; padding: 1rem; border-radius: 10px; 
                 border-left: 4px solid #3498db; margin: 0.5rem 0; }
    .truck-status { padding: 0.5rem 1rem; border-radius: 20px; font-weight: 500; }
    .status-moving { background: #d4edda; color: #155724; }
    .status-stopped { background: #f8d7da; color: #721c24; }
    .help-btn { position: fixed; bottom: 20px; right: 20px; z-index: 999; }
</style>
""", unsafe_allow_html=True)


def init_state():
    """Initialize session state."""
    defaults = {
        'initialized': True, 'events': [], 'index': 0, 'mode': 'theft',
        'running': False, 'total_weight': 5000,
        'stop_analyzer': StopAnalyzer(),
        'weight_analyzer': EnhancedWeightAnalyzer(),
        'escalation': EscalationEngine(),
        'camera': EnhancedCameraSimulator(),
        'detector': SimpleAIDetector(),
        'baseline_set': False, 'cam_mode': 'standby', 'gps_mode': 'normal',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_analyzers():
    """Reset analyzers."""
    st.session_state.stop_analyzer = StopAnalyzer()
    st.session_state.weight_analyzer = EnhancedWeightAnalyzer()
    st.session_state.escalation = EscalationEngine()
    st.session_state.baseline_set = False
    st.session_state.cam_mode = 'standby'


def generate_events(mode: str):
    """Generate events."""
    weight = st.session_state.total_weight
    if mode == 'theft':
        sim = TransitSimulator(truck_id="TS-JH-1002", initial_weight_kg=weight)
        return sim.generate_pilferage_scenario(pilferage_at_progress=0.4, weight_stolen_kg=500, stop_duration_min=20)
    else:
        sim = TransitSimulator(truck_id="TS-JH-1001", initial_weight_kg=weight)
        return sim.generate_normal_journey()


def process_event(event: dict):
    """Process event."""
    stop_result = st.session_state.stop_analyzer.process_reading(event)
    weight_result = st.session_state.weight_analyzer.process_reading(event)
    
    if stop_result and stop_result.is_suspicious:
        st.session_state.escalation.process_stop_event(stop_result)
    if weight_result and weight_result.is_suspicious:
        st.session_state.escalation.process_weight_alert(weight_result)
        st.session_state.cam_mode = 'active'
    
    st.session_state.gps_mode = 'low_power' if event.get('speed_kmh', 0) > 60 else 'high_freq'


def render_quick_stats():
    """Render quick stats with cards."""
    stats = historical_service.get_fleet_stats()
    
    cols = st.columns(6)
    
    cards = [
        (cols[0], f"{stats['active_trucks']}", "🚛 Active Trucks", "stat-card-blue"),
        (cols[1], f"{stats['trips_today']}", "📦 Trips Today", "stat-card-green"),
        (cols[2], f"{stats['alerts_today']}", "⚠️ Alerts Today", "stat-card-orange"),
        (cols[3], f"{stats['thefts_this_month']}", "🚨 Monthly Thefts", "stat-card-red"),
        (cols[4], f"₹{stats['prevented_loss']/100000:.0f}L", "💰 Saved", "stat-card"),
        (cols[5], f"{int(stats['recovery_rate']*100)}%", "✅ Recovery", "stat-card-green"),
    ]
    
    for col, value, label, card_class in cards:
        with col:
            st.markdown(f'''
            <div class="stat-card {card_class}">
                <div class="stat-number">{value}</div>
                <div class="stat-label">{label}</div>
            </div>
            ''', unsafe_allow_html=True)


def render_traffic_status(lat: float, lon: float):
    """Render traffic and risk status."""
    traffic = traffic_service.get_traffic_status(lat, lon)
    risk = traffic_service.get_route_risk(lat, lon)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        traffic_color = {'light': '🟢', 'moderate': '🟡', 'heavy': '🟠', 'jam': '🔴'}
        st.markdown(f"**🚦 Traffic:** {traffic_color.get(traffic.condition, '⚪')} {traffic.condition.upper()}")
    
    with col2:
        risk_color = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}
        st.markdown(f"**⚠️ Route Risk:** {risk_color.get(risk['risk_level'], '⚪')} {risk['risk_level'].upper()}")
    
    with col3:
        mode_icon = "🌙 Night Mode" if is_night_time() else "☀️ Day Mode"
        st.markdown(f"**📹 Camera:** {mode_icon}")


def render_gauges(event: dict):
    """Render speed and weight gauges."""
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=event['speed_kmh'],
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Speed (km/h)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#3498db"},
                'steps': [
                    {'range': [0, 30], 'color': "#e8f4fc"},
                    {'range': [30, 60], 'color': "#d1e7f5"},
                    {'range': [60, 100], 'color': "#bbd9ed"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0 if not event['is_moving'] else 100
                }
            }
        ))
        fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        weight_pct = (event['weight_kg'] / st.session_state.total_weight) * 100
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=event['weight_kg'],
            delta={'reference': st.session_state.total_weight, 'relative': False},
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Weight (kg)"},
            gauge={
                'axis': {'range': [0, st.session_state.total_weight + 500]},
                'bar': {'color': "#27ae60" if weight_pct > 95 else "#e74c3c"},
                'steps': [
                    {'range': [0, st.session_state.total_weight * 0.9], 'color': "#fadbd8"},
                    {'range': [st.session_state.total_weight * 0.9, st.session_state.total_weight], 'color': "#d5f4e6"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': st.session_state.total_weight - 100
                }
            }
        ))
        fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)


def render_camera(event: dict):
    """Render camera feed."""
    cam = st.session_state.camera
    detector = st.session_state.detector
    cam.set_night_mode(is_night_time())
    
    if not st.session_state.baseline_set:
        baseline, _ = cam.generate_normal_cargo_image()
        detector.set_baseline(baseline)
        st.session_state.baseline_set = True
    
    is_theft = event.get('scenario') == 'pilferage'
    is_stopped = not event.get('is_moving', True)
    
    if is_theft and is_stopped:
        img, persons = cam.generate_theft_image(5)
    else:
        img, persons = cam.generate_normal_cargo_image()
    
    result = detector.analyze_frame(img)
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        mode_icon = "🌙 IR Night Vision" if is_night_time() else "☀️ Day Camera"
        st.markdown(f"**🔴 LIVE** | {mode_icon}")
        st.image(img, use_container_width=True)
    
    with col2:
        st.markdown("**🤖 AI Analysis**")
        
        if result.alert_level == 'critical':
            st.error(f"🚨 ALERT: {len(persons)} person(s) detected near cargo!")
        elif result.alert_level == 'warning':
            st.warning(f"⚠️ {result.details}")
        else:
            st.success("✅ All clear - No threats detected")
        
        # Metrics with gauge-like display
        col_a, col_b = st.columns(2)
        col_a.metric("Cargo Change", f"{result.cargo_change_percent:.0f}%",
                    delta=f"-{result.cargo_change_percent:.0f}%" if result.cargo_change_detected else None,
                    delta_color="inverse")
        col_b.metric("Persons", result.persons_detected,
                    delta="ALERT!" if result.persons_detected > 0 else None,
                    delta_color="inverse")
        
        # Person details
        if result.persons_detected > 0:
            st.markdown("**👥 Detected Persons:**")
            for i, p in enumerate(persons, 1):
                st.progress(p.bbox.confidence, text=f"Person {i}: {p.bbox.confidence:.0%} confidence")
        
        # Action buttons
        if result.alert_level in ['critical', 'warning']:
            st.divider()
            c1, c2, c3 = st.columns(3)
            if c1.button("📞 Call", use_container_width=True, key="call"):
                st.toast("📞 Calling driver...", icon="📱")
            if c2.button("🚔 Security", use_container_width=True, key="sec"):
                st.toast("🚔 Security dispatched!", icon="🚨")
            if c3.button("📥 Evidence", use_container_width=True, key="ev"):
                st.toast("📥 Evidence saved!", icon="✅")


def render_map(event: dict):
    """Render enhanced map."""
    try:
        import folium
        from streamlit_folium import st_folium
        
        m = folium.Map(location=[event['latitude'], event['longitude']], zoom_start=10)
        
        # Route line
        if st.session_state.events:
            route_points = [[e['latitude'], e['longitude']] 
                           for e in st.session_state.events[:st.session_state.index + 1]]
            folium.PolyLine(route_points, color='blue', weight=3, opacity=0.7).add_to(m)
        
        # Geofences with labels
        for z in AUTHORIZED_ZONES:
            folium.Circle(
                [z.latitude, z.longitude], 
                radius=z.radius_km*1000,
                color='green', fill=True, fillOpacity=0.15,
                popup=f"<b>{z.name}</b><br>{z.zone_type}"
            ).add_to(m)
        
        # Truck marker
        is_alert = not event.get('is_moving') and not event.get('in_authorized_zone')
        color = 'red' if is_alert else 'green' if event.get('is_moving') else 'orange'
        
        folium.Marker(
            [event['latitude'], event['longitude']], 
            popup=f"<b>{event['truck_id']}</b><br>Speed: {event['speed_kmh']} km/h<br>Weight: {event['weight_kg']} kg",
            icon=folium.Icon(color=color, icon='truck', prefix='fa')
        ).add_to(m)
        
        st_folium(m, width=None, height=350, returned_objects=[])
    except ImportError:
        st.info(f"📍 Location: ({event['latitude']:.4f}, {event['longitude']:.4f})")


def render_theft_history():
    """Render theft history panel."""
    st.subheader("📊 Recent Incidents")
    
    records = historical_service.get_recent_thefts(3)
    
    for r in records:
        status = "✅ Recovered" if r.recovered else "❌ Not Recovered"
        st.markdown(f"""
        <div class="info-card">
            <strong>{r.date.strftime('%d %b')}</strong> | {r.location}<br>
            <span style="color:#e74c3c">⚖️ {r.weight_stolen_kg:.0f}kg</span> | 
            ₹{r.value_inr/1000:.0f}K | {status}
        </div>
        """, unsafe_allow_html=True)


def main():
    init_state()
    
    # Header with help link
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown('<h1 class="main-header">🚛 Tata Steel Anti-Theft Monitor</h1>', unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style='text-align:right; padding-top:0.5rem'>
            <a href='http://localhost:8502' target='_blank' style='text-decoration:none;'>
                📖 User Guide
            </a> | 🔋87% | {datetime.now().strftime('%H:%M')}
        </div>
        """, unsafe_allow_html=True)
    
    # Quick Stats
    render_quick_stats()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Control Panel
    st.markdown("### 🎮 Control Panel")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        theft_btn = st.button("🔴 Theft Demo", use_container_width=True, 
                             type="primary" if st.session_state.mode == 'theft' and st.session_state.events else "secondary")
    with c2:
        normal_btn = st.button("🟢 Normal Demo", use_container_width=True)
    with c3:
        reset_btn = st.button("⏮️ Reset", use_container_width=True)
    with c4:
        play_btn = st.button("▶️ Play", use_container_width=True)
    with c5:
        stop_btn = st.button("⏹️ Stop", use_container_width=True)
    
    if theft_btn:
        st.session_state.mode = 'theft'
        st.session_state.events = generate_events('theft')
        st.session_state.index = 0
        reset_analyzers()
        st.rerun()
    if normal_btn:
        st.session_state.mode = 'normal'
        st.session_state.events = generate_events('normal')
        st.session_state.index = 0
        reset_analyzers()
        st.rerun()
    if reset_btn:
        st.session_state.index = 0
        reset_analyzers()
        st.rerun()
    if play_btn:
        st.session_state.running = True
    if stop_btn:
        st.session_state.running = False
    
    st.divider()
    
    # Main content
    if not st.session_state.events:
        st.info("👆 Click **🔴 Theft Demo** to see the system catch a theft in action!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🎯 Quick Overview")
            st.markdown("""
            This system monitors Tata Steel trucks in real-time to prevent rebar theft:
            
            - **📡 GPS Tracking** - Know where every truck is
            - **⚖️ Weight Sensors** - Detect cargo removal instantly  
            - **📹 AI Camera** - Identify unauthorized persons
            - **🚨 Smart Alerts** - 4-level escalation to security
            """)
        
        with col2:
            render_theft_history()
        return
    
    # Current event
    idx = min(st.session_state.index, len(st.session_state.events) - 1)
    event = st.session_state.events[idx]
    process_event(event)
    
    # Status banner
    active_alerts = st.session_state.escalation.get_active_alerts()
    has_critical = any(a.level >= AlertLevel.CRITICAL for a in active_alerts)
    
    if has_critical:
        st.markdown('''
        <div class="alert-banner alert-critical">
            <span style="font-size:1.5rem; margin-right:1rem;">🚨</span>
            <span><strong>THEFT ALERT</strong> - Unauthorized cargo removal detected! Camera activated.</span>
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown('''
        <div class="alert-banner alert-normal">
            <span style="font-size:1.5rem; margin-right:1rem;">✅</span>
            <span><strong>Normal Operation</strong> - All systems green. No threats detected.</span>
        </div>
        ''', unsafe_allow_html=True)
    
    # Traffic status
    render_traffic_status(event['latitude'], event['longitude'])
    
    st.divider()
    
    # Timeline
    max_idx = len(st.session_state.events) - 1
    new_idx = st.slider("⏱️ Journey Timeline", 0, max_idx, idx, 
                       help="Drag to navigate through the truck's journey")
    
    if new_idx != st.session_state.index:
        st.session_state.index = new_idx
        reset_analyzers()
        for i in range(new_idx + 1):
            process_event(st.session_state.events[i])
        st.rerun()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress((idx + 1) / (max_idx + 1))
    with col2:
        st.caption(f"Event {idx + 1} / {max_idx + 1}")
    
    st.divider()
    
    # Speed & Weight Gauges
    render_gauges(event)
    
    st.divider()
    
    # Map and Camera/Alerts
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.subheader("📍 Live GPS Tracking")
        render_map(event)
    
    with col_right:
        if has_critical or (event.get('scenario') == 'pilferage' and not event.get('is_moving')):
            st.subheader("📹 Camera Active")
            render_camera(event)
        else:
            st.subheader("🚨 Alert Status")
            summary = st.session_state.escalation.get_alert_summary()
            
            cols = st.columns(4)
            cols[0].metric("🟡 Watch", summary['by_level']['watchlist'])
            cols[1].metric("🟠 Warn", summary['by_level']['warning'])
            cols[2].metric("🔴 Critical", summary['by_level']['critical'])
            cols[3].metric("🚨 Emergency", summary['by_level']['emergency'])
            
            if active_alerts:
                for a in active_alerts[:2]:
                    st.warning(f"**{a.title}**")
            else:
                st.success("✅ All systems operating normally")
    
    st.divider()
    
    # Charts
    col1, col2 = st.columns(2)
    df = pd.DataFrame(st.session_state.events[:idx + 1])
    
    with col1:
        st.subheader("⚖️ Weight Trend")
        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['weight_kg'], 
                                    fill='tozeroy', fillcolor='rgba(39, 174, 96, 0.3)',
                                    line=dict(color='#27ae60', width=2)))
            fig.add_hline(y=st.session_state.total_weight - 100, line_dash="dash", 
                         line_color="red", annotation_text="Alert Threshold")
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0),
                            yaxis_title="Weight (kg)", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⚡ Speed Trend")
        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['speed_kmh'],
                                    line=dict(color='#3498db', width=2)))
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0),
                            yaxis_title="Speed (km/h)", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    
    # Auto-play
    if st.session_state.running and st.session_state.index < max_idx:
        time.sleep(0.15)
        st.session_state.index += 1
        process_event(st.session_state.events[st.session_state.index])
        st.rerun()
    elif st.session_state.running:
        st.session_state.running = False
        st.toast("✅ Simulation complete!", icon="🎉")


if __name__ == "__main__":
    main()
