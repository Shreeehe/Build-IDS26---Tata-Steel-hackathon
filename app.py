"""
Tata Steel Rebar Anti-Theft Monitor
Clean, Professional Dashboard - Core Focus: Pilferage Detection
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data.simulator import TransitSimulator
from src.data.geofences import AUTHORIZED_ZONES
from src.data.services import traffic_service
from src.engine.stop_analyzer import StopAnalyzer
from src.engine.weight_analyzer import EnhancedWeightAnalyzer
from src.engine.escalation import EscalationEngine, AlertLevel
from src.camera.simulator import EnhancedCameraSimulator, is_night_time
from src.camera.detector import SimpleAIDetector

st.set_page_config(
    page_title="Tata Steel - Anti-Theft Monitor",
    page_icon="🚛",
    layout="wide"
)

# Clean, minimal CSS
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .main-header { font-size: 1.8rem; font-weight: 600; color: #1d1d1f; letter-spacing: -0.5px; }
    .status-pill { display: inline-block; padding: 0.4rem 1rem; border-radius: 20px; font-weight: 500; font-size: 0.85rem; }
    .status-safe { background: #d1f2eb; color: #0d6b4e; }
    .status-alert { background: #fadbd8; color: #c0392b; }
    .metric-card { background: #f5f5f7; padding: 1.2rem; border-radius: 12px; text-align: center; }
    .metric-value { font-size: 1.8rem; font-weight: 600; color: #1d1d1f; }
    .metric-label { font-size: 0.75rem; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; }
    .alert-banner { padding: 1rem 1.5rem; border-radius: 12px; margin: 1rem 0; }
    .alert-critical { background: linear-gradient(135deg, #ff3b30, #ff2d55); color: white; }
    .alert-safe { background: linear-gradient(135deg, #34c759, #30d158); color: white; }
    .section-title { font-size: 0.9rem; font-weight: 600; color: #86868b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.8rem; }
    div[data-testid="stButton"] button { border-radius: 20px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)


def init_state():
    defaults = {
        'events': [], 'index': 0, 'mode': 'theft', 'running': False,
        'total_weight': 5000,
        'stop_analyzer': StopAnalyzer(),
        'weight_analyzer': EnhancedWeightAnalyzer(),
        'escalation': EscalationEngine(),
        'camera': EnhancedCameraSimulator(),
        'detector': SimpleAIDetector(),
        'baseline_set': False, 'cam_mode': 'standby',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset():
    st.session_state.stop_analyzer = StopAnalyzer()
    st.session_state.weight_analyzer = EnhancedWeightAnalyzer()
    st.session_state.escalation = EscalationEngine()
    st.session_state.baseline_set = False
    st.session_state.cam_mode = 'standby'


def generate_events(mode: str):
    weight = st.session_state.total_weight
    if mode == 'theft':
        sim = TransitSimulator(truck_id="TS-JH-1002", initial_weight_kg=weight)
        return sim.generate_pilferage_scenario(pilferage_at_progress=0.4, weight_stolen_kg=500, stop_duration_min=20)
    sim = TransitSimulator(truck_id="TS-JH-1001", initial_weight_kg=weight)
    return sim.generate_normal_journey()


def process_event(event: dict):
    stop_result = st.session_state.stop_analyzer.process_reading(event)
    weight_result = st.session_state.weight_analyzer.process_reading(event)
    
    if stop_result and stop_result.is_suspicious:
        st.session_state.escalation.process_stop_event(stop_result)
    if weight_result and weight_result.is_suspicious:
        st.session_state.escalation.process_weight_alert(weight_result)
        st.session_state.cam_mode = 'active'


def render_camera(event: dict):
    cam = st.session_state.camera
    detector = st.session_state.detector
    cam.set_night_mode(is_night_time())
    
    if not st.session_state.baseline_set:
        baseline, _ = cam.generate_normal_cargo_image()
        detector.set_baseline(baseline)
        st.session_state.baseline_set = True
    
    is_theft = event.get('scenario') == 'pilferage' and not event.get('is_moving', True)
    
    if is_theft:
        img, persons = cam.generate_theft_image(5)
    else:
        img, persons = cam.generate_normal_cargo_image()
    
    result = detector.analyze_frame(img)
    
    col1, col2 = st.columns([1.3, 1])
    
    with col1:
        st.image(img, use_container_width=True)
    
    with col2:
        if result.persons_detected > 0:
            st.error(f"🚨 **{result.persons_detected} Person(s) Detected**")
        else:
            st.success("✅ **No Threats**")
        
        st.metric("Cargo Integrity", f"{100 - result.cargo_change_percent:.0f}%")
        
        if result.persons_detected > 0:
            for i, p in enumerate(persons, 1):
                st.caption(f"Person {i} • {p.bbox.confidence:.0%} confidence")
            
            st.divider()
            c1, c2 = st.columns(2)
            if c1.button("📞 Call Driver", use_container_width=True):
                st.toast("Calling driver...")
            if c2.button("🚔 Alert Security", use_container_width=True):
                st.toast("Security dispatched!")


def render_map(event: dict):
    try:
        import folium
        from streamlit_folium import st_folium
        
        m = folium.Map(location=[event['latitude'], event['longitude']], zoom_start=10, 
                      tiles='cartodbpositron')
        
        # Route
        if st.session_state.events:
            route = [[e['latitude'], e['longitude']] for e in st.session_state.events[:st.session_state.index + 1]]
            folium.PolyLine(route, color='#007aff', weight=3, opacity=0.8).add_to(m)
        
        # Zones
        for z in AUTHORIZED_ZONES:
            folium.Circle([z.latitude, z.longitude], radius=z.radius_km*1000,
                         color='#34c759', fill=True, fillOpacity=0.1).add_to(m)
        
        # Truck
        is_alert = not event.get('is_moving') and not event.get('in_authorized_zone')
        folium.Marker(
            [event['latitude'], event['longitude']],
            icon=folium.Icon(color='red' if is_alert else 'blue', icon='truck', prefix='fa')
        ).add_to(m)
        
        st_folium(m, height=320, returned_objects=[])
    except:
        st.info(f"📍 {event['latitude']:.4f}, {event['longitude']:.4f}")


def main():
    init_state()
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1 class="main-header">🚛 Anti-Theft Monitor</h1>', unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='text-align:right; padding-top:0.5rem; color:#86868b;'>{datetime.now().strftime('%H:%M')} • <a href='https://guide-tata-steel.streamlit.app/' target='_blank'>Help</a></div>", unsafe_allow_html=True)
    
    # Controls
    c1, c2, c3, c4, c5 = st.columns(5)
    
    if c1.button("🔴 Theft Demo", use_container_width=True, type="primary" if not st.session_state.events or st.session_state.mode == 'theft' else "secondary"):
        st.session_state.mode = 'theft'
        st.session_state.events = generate_events('theft')
        st.session_state.index = 0
        reset()
        st.rerun()
    
    if c2.button("🟢 Normal Demo", use_container_width=True):
        st.session_state.mode = 'normal'
        st.session_state.events = generate_events('normal')
        st.session_state.index = 0
        reset()
        st.rerun()
    
    if c3.button("⏮️ Reset", use_container_width=True):
        st.session_state.index = 0
        reset()
        st.rerun()
    
    if c4.button("▶️ Play", use_container_width=True):
        st.session_state.running = True
    
    if c5.button("⏹️ Stop", use_container_width=True):
        st.session_state.running = False
    
    st.divider()
    
    # Empty state
    if not st.session_state.events:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("""
            <div style='padding:2rem 0; color:#86868b;'>
                <p style='font-size:2.5rem; margin-bottom:0.5rem;'>🚛</p>
                <h2 style='color:#1d1d1f;'>Rebar Anti-Theft System</h2>
                <p style='font-size:1rem; line-height:1.6;'>
                    Click <strong>Theft Demo</strong> to see the system detect pilferage in real-time.
                </p>
                <br>
                <p style='font-size:0.9rem;'>
                    <strong>🔴 Red Dot</strong> = AI Camera Position<br>
                    <strong>🔺 Red Zone</strong> = Camera Coverage Area
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.image("assets/camera_setup.png", caption="Camera monitors cargo from rear of truck", use_container_width=True)
        
        return
    
    # Current event
    idx = min(st.session_state.index, len(st.session_state.events) - 1)
    event = st.session_state.events[idx]
    process_event(event)
    
    # Status
    alerts = st.session_state.escalation.get_active_alerts()
    has_critical = any(a.level >= AlertLevel.CRITICAL for a in alerts)
    
    if has_critical:
        st.markdown('<div class="alert-banner alert-critical"><strong>🚨 Theft Detected</strong> — Unauthorized cargo removal in progress</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-banner alert-safe"><strong>✅ All Clear</strong> — Transit proceeding normally</div>', unsafe_allow_html=True)
    
    # Key Metrics
    st.markdown('<p class="section-title">Live Status</p>', unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{event["speed_kmh"]:.0f}</div><div class="metric-label">Speed (km/h)</div></div>', unsafe_allow_html=True)
    
    with m2:
        weight_loss = st.session_state.total_weight - event['weight_kg']
        color = "#ff3b30" if weight_loss > 100 else "#1d1d1f"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{color}">{event["weight_kg"]:,.0f}</div><div class="metric-label">Weight (kg)</div></div>', unsafe_allow_html=True)
    
    with m3:
        status = "Moving" if event['is_moving'] else "Stopped"
        st.markdown(f'<div class="metric-card"><div class="metric-value">{"🟢" if event["is_moving"] else "🔴"}</div><div class="metric-label">{status}</div></div>', unsafe_allow_html=True)
    
    with m4:
        zone = "Yes" if event.get('in_authorized_zone') else "No"
        st.markdown(f'<div class="metric-card"><div class="metric-value">{"✅" if event.get("in_authorized_zone") else "⚠️"}</div><div class="metric-label">In Zone: {zone}</div></div>', unsafe_allow_html=True)
    
    # Timeline
    max_idx = len(st.session_state.events) - 1
    new_idx = st.slider("Timeline", 0, max_idx, idx, label_visibility="collapsed")
    
    if new_idx != st.session_state.index:
        st.session_state.index = new_idx
        reset()
        for i in range(new_idx + 1):
            process_event(st.session_state.events[i])
        st.rerun()
    
    st.divider()
    
    # Main content
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.markdown('<p class="section-title">Location</p>', unsafe_allow_html=True)
        render_map(event)
    
    with col_right:
        if has_critical or (event.get('scenario') == 'pilferage' and not event.get('is_moving')):
            st.markdown('<p class="section-title">Camera Feed</p>', unsafe_allow_html=True)
            render_camera(event)
        else:
            st.markdown('<p class="section-title">Alert Status</p>', unsafe_allow_html=True)
            summary = st.session_state.escalation.get_alert_summary()
            
            cols = st.columns(4)
            cols[0].metric("Watch", summary['by_level']['watchlist'])
            cols[1].metric("Warn", summary['by_level']['warning'])
            cols[2].metric("Critical", summary['by_level']['critical'])
            cols[3].metric("Emergency", summary['by_level']['emergency'])
            
            if not alerts:
                st.info("No active alerts")
    
    st.divider()
    
    # Weight Chart
    st.markdown('<p class="section-title">Weight Over Time</p>', unsafe_allow_html=True)
    
    df = pd.DataFrame(st.session_state.events[:idx + 1])
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['weight_kg'],
            fill='tozeroy', fillcolor='rgba(0,122,255,0.1)',
            line=dict(color='#007aff', width=2)
        ))
        fig.add_hline(y=st.session_state.total_weight - 100, line_dash="dot", 
                     line_color="#ff3b30", annotation_text="Alert Threshold")
        fig.update_layout(
            height=200, 
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis_title="kg",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Auto-play
    if st.session_state.running and st.session_state.index < max_idx:
        time.sleep(0.15)
        st.session_state.index += 1
        process_event(st.session_state.events[st.session_state.index])
        st.rerun()
    elif st.session_state.running:
        st.session_state.running = False


if __name__ == "__main__":
    main()
