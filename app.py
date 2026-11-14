import json
import urllib.request
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Rishi's Home Guardian", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

LPG_MOD, LPG_CRIT = 150, 300
TEMP_MOD, TEMP_CRIT = 38, 48
FLOOD_MOD, FLOOD_CRIT = 5, 10
OVERCURRENT_CRIT = 25.0

def stage_of(val, mod_v, crit_v):
    return "CRITICAL" if val >= crit_v else ("MODERATE" if val >= mod_v else "SAFE")

@st.cache_data(ttl=300)
def get_hyderabad_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=17.3850&longitude=78.4867&current=temperature_2m,rain,weather_code"
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            cur = json.loads(resp.read().decode())["current"]
            return cur["temperature_2m"], cur["rain"], cur["weather_code"]
    except Exception:
        return None, 0.0, 0

st.markdown("""
<style>
.app-header { display:flex; align-items:center; gap:14px; padding:14px 20px; border-radius:14px; margin-bottom:14px; box-shadow:0 4px 16px rgba(15,23,42,0.2); }
.app-header, .app-header * { color: #f8fafc !important; }
.hdr-safe { background: linear-gradient(90deg, #0f172a, #064e3b); border: 1px solid #10b981; }
.hdr-mod  { background: linear-gradient(90deg, #451a03, #78350f); border: 1px solid #f59e0b; }
.hdr-crit { background: linear-gradient(90deg, #450a0a, #7f1d1d); border: 1px solid #ef4444; }
.app-logo { font-size:2rem; background:rgba(255,255,255,0.12); padding:8px 14px; border-radius:12px; }
div[data-testid="stMetric"] { background:linear-gradient(135deg,#0f172a,#1e293b); border:1px solid rgba(56,189,248,0.35); padding:14px 18px; border-radius:12px; }
div[data-testid="stMetric"] label, div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color:#f8fafc !important; }
div[role="radiogroup"] { gap:8px; background:rgba(148,163,184,0.14); padding:6px; border-radius:12px; }
div[role="radiogroup"] > label { background:transparent; padding:6px 14px; border-radius:8px; margin:0 !important; }
</style>
""", unsafe_allow_html=True)

DEFAULT_APPLIANCES = {
    "Bedroom": {
        "Bedroom Fan": {"watts": 75, "on": True, "pos": [-2.5, 2.05, -3.2], "type": "fan"},
        "Bedroom AC": {"watts": 1500, "on": False, "pos": [-6.2, 1.75, -3.2], "type": "ac"},
        "Bedroom Tube Light": {"watts": 20, "on": True, "pos": [-2.5, 2.0, -1.15], "type": "tube"},
    },
    "Bathroom": {
        "Bathroom Light": {"watts": 12, "on": True, "pos": [3.15, 2.0, -1.15], "type": "bulb"},
        "Geyser / Water Heater": {"watts": 2000, "on": False, "pos": [4.55, 1.55, -3.2], "type": "geyser"},
    },
    "Hall": {
        "Hall TV": {"watts": 120, "on": True, "pos": [-2.5, 1.15, 4.78], "type": "tv"},
        "Hall AC": {"watts": 1500, "on": False, "pos": [-5.7, 1.75, 2.0], "type": "ac"},
        "Hall Fan 1": {"watts": 75, "on": True, "pos": [-4.0, 2.05, 1.8], "type": "fan"},
        "Hall Fan 2": {"watts": 75, "on": True, "pos": [-1.0, 2.05, 1.8], "type": "fan"},
        "Hall Tube Lights (x2)": {"watts": 40, "on": True, "pos": [-2.5, 2.0, -0.82], "type": "tube"},
        "Hall Ceiling Lights": {"watts": 30, "on": True, "pos": [-2.5, 2.05, 3.3], "type": "bulb"},
    },
    "Kitchen": {
        "Refrigerator": {"watts": 150, "on": True, "pos": [2.0, 0.75, -0.35], "type": "fridge"},
        "Chimney / Exhaust Fan": {"watts": 180, "on": True, "pos": [5.4, 1.75, 2.5], "type": "chimney"},
        "Kitchen Lights": {"watts": 20, "on": True, "pos": [3.5, 2.05, 1.2], "type": "bulb"},
    },
}

if "appliances" not in st.session_state: st.session_state.appliances = DEFAULT_APPLIANCES
if "circuits" not in st.session_state: st.session_state.circuits = {"Main Breaker": True, "LPG Solenoid Valve": True}
if "logs" not in st.session_state: st.session_state.logs = []
if "history" not in st.session_state: st.session_state.history = [{"Time": "09:00", "LPG (ppm)": 90, "Kitchen (°C)": 30, "Flood (cm)": 0, "Power (W)": 570}]
if "client" not in st.session_state:
    st.session_state.client = {"name": "Rishi", "address": "Hyderabad, Telangana", "phone": "+91-XXXXXXXXXX", "family": "+91-XXXXXXXXXX"}

for room, items in st.session_state.appliances.items():
    for name, info in items.items():
        k = f"app_{room}_{name}"
        if k in st.session_state: info["on"] = st.session_state[k]

with st.sidebar:
    st.markdown("## 🛡️ Rishi's Black Box")
    st.caption(f"Triggers: Gas >= {LPG_CRIT} ppm • Temp >= {TEMP_CRIT}°C • Flood >= {FLOOD_CRIT} cm")
    st.divider()
    st.subheader("🔥 Gas & Thermal (3-Stage)")
    leak_source = st.selectbox("Gas / Refrigerant Leak Source", ["None", "Kitchen LPG Cylinder", "Bedroom AC (Refrigerant)", "Hall AC (Refrigerant)", "Kitchen Refrigerator"])
    lpg = st.slider("Gas Concentration (ppm)", 50, 1000, 340 if leak_source != "None" else 90)
    kitchen_temp = st.slider("Kitchen Temp (°C)", 22, 85, 31)
    flame = st.checkbox("IR Flame Sensor Triggered")
    smoke = st.checkbox("Optical Smoke Sensor Triggered")

    st.divider()
    st.subheader("⚡ Electrical Faults & SC")
    earth_leak = st.checkbox("Electrical Earth Leakage (>30 mA)")
    sc_room = st.selectbox("Simulate Short Circuit (SC) in Room", ["None", "Bedroom", "Bathroom", "Hall", "Kitchen"])

    st.divider()
    st.subheader("🌧️ Outdoor Weather & Flood")
    use_live_wx = st.toggle("🌦️ Live Hyderabad Weather", value=True)
    if use_live_wx:
        live_t, live_rain, wmo = get_hyderabad_weather()
        if live_t is not None:
            st.caption(f"Hyderabad Live: {live_t}°C • Rain: {live_rain} mm")
            weather = "Severe Flood" if live_rain >= 10 else ("Heavy Rain" if (live_rain > 0 or wmo >= 51) else "Clear Sky")
        else:
            weather = st.selectbox("Weather Condition", ["Clear Sky", "Heavy Rain", "Severe Flood"])
    else:
        weather = st.selectbox("Weather Condition", ["Clear Sky", "Heavy Rain", "Severe Flood"])
    flood_cm = st.slider("Flood Water Level (cm)", 0, 40, 14 if weather == "Severe Flood" else (6 if weather == "Heavy Rain" else 0))

    if st.button("📸 Save Snapshot", use_container_width=True):
        st.session_state.history.append({
            "Time": datetime.now().strftime("%H:%M:%S"), "LPG (ppm)": lpg, "Kitchen (°C)": kitchen_temp, "Flood (cm)": flood_cm,
            "Power (W)": sum(a["watts"] for items in st.session_state.appliances.values() for a in items.values() if a["on"]) if st.session_state.circuits["Main Breaker"] else 0,
        })

lpg_stage, temp_stage, flood_stage = stage_of(lpg, LPG_MOD, LPG_CRIT), stage_of(kitchen_temp, TEMP_MOD, TEMP_CRIT), stage_of(flood_cm, FLOOD_MOD, FLOOD_CRIT)
main_on = st.session_state.circuits["Main Breaker"]
room_watts = {r: (0 if (not main_on or r == sc_room) else sum(a["watts"] for a in items.values() if a["on"])) for r, items in st.session_state.appliances.items()}
total_watts = sum(room_watts.values())
current_a = round(total_watts / 230.0, 2)

crit_reasons, mod_reasons = [], []
if lpg_stage == "CRITICAL": crit_reasons.append(f"Gas Leak ({lpg} ppm • {leak_source if leak_source != 'None' else 'Kitchen'})")
elif lpg_stage == "MODERATE": mod_reasons.append(f"Elevated Gas ({lpg} ppm)")
if temp_stage == "CRITICAL": crit_reasons.append(f"High Temp ({kitchen_temp}°C)")
elif temp_stage == "MODERATE": mod_reasons.append(f"Warm Kitchen ({kitchen_temp}°C)")
if flood_stage == "CRITICAL": crit_reasons.append(f"Flood Electrocution Risk ({flood_cm} cm)")
elif flood_stage == "MODERATE": mod_reasons.append(f"Waterlogging ({flood_cm} cm)")
if flame: crit_reasons.append("Flame Detected")
if smoke: crit_reasons.append("Smoke Detected")
if earth_leak: crit_reasons.append("Electrical Earth Leakage (>30 mA)")
if sc_room != "None": crit_reasons.append(f"Short Circuit + Fire Sparks in {sc_room}")
if current_a > OVERCURRENT_CRIT: crit_reasons.append(f"Overload ({current_a} A)")

if crit_reasons:
    st.session_state.circuits["Main Breaker"] = False
    if lpg_stage == "CRITICAL" or flame or smoke or temp_stage == "CRITICAL":
        st.session_state.circuits["LPG Solenoid Valve"] = False
    main_on, total_watts, current_a = False, 0, 0.0
    room_watts = {r: 0 for r in room_watts}
    msg = "CRITICAL TRIP: " + ", ".join(crit_reasons)
    if not st.session_state.logs or st.session_state.logs[0]["Event"] != msg:
        st.session_state.logs.insert(0, {"Time": datetime.now().strftime("%I:%M:%S %p"), "Event": msg, "Action": "MCB/ELCB & Valve Cut"})

risk_score = min(100, int((min(lpg, 500)/500)*35 + (max(0, kitchen_temp-25)/35)*20 + (min(flood_cm, 15)/15)*30 + (30 if (flame or smoke) else 0) + (35 if (sc_room != "None" or earth_leak) else 0)))
hdr_cls = "hdr-crit" if crit_reasons else ("hdr-mod" if mod_reasons else "hdr-safe")
status_txt = "🚨 CRITICAL" if crit_reasons else ("⚠️ MODERATE" if mod_reasons else "✅ SAFE")

st.markdown(f"""
<div class="app-header {hdr_cls}">
    <div class="app-logo">🛡️</div>
    <div>
        <div style="font-size:1.3rem; font-weight:700;">{st.session_state.client['name']}'s Home Guardian 1BHK — Life-Safety Intelligence</div>
        <div style="font-size:0.88rem; opacity:0.92;">
            Stage: <b>{status_txt}</b> • Gas: <b>{lpg} ppm ({lpg_stage})</b> • Temp: <b>{kitchen_temp}°C ({temp_stage})</b> • Flood: <b>{flood_cm} cm ({flood_stage})</b> • Load: <b>{total_watts} W ({current_a} A)</b>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

page = st.radio("Navigation", ["🏠 3D 1BHK House", "📊 Overview", "⚡ Power", "🔌 Controls", "🚨 Emergency", "📼 Black Box"], horizontal=True, label_visibility="collapsed")

if page == "🏠 3D 1BHK House":
    col_view, col_panel = st.columns([2.35, 1])
    with col_panel:
        st.subheader("💡 Room Appliances")
        for room, items in st.session_state.appliances.items():
            tag = " ⚡SC TRIP" if room == sc_room else ""
            with st.expander(f"{room} — {room_watts[room]} W{tag}", expanded=(room in ["Hall", "Bedroom", "Kitchen"])):
                for name, info in items.items():
                    st.toggle(f"{name} ({info['watts']} W)", value=info["on"], key=f"app_{room}_{name}")

    with col_view:
        scene_items = [{"room": r, "name": n, "watts": i["watts"] if (i["on"] and main_on and r != sc_room) else 0, "amps": round((i["watts"] if (i["on"] and main_on and r != sc_room) else 0)/230.0, 2), "on": bool(i["on"] and main_on and r != sc_room), "pos": i["pos"], "type": i["type"]} for r, items in st.session_state.appliances.items() for n, i in items.items()]
        leak_coords = {"Kitchen LPG Cylinder": [4.1, 0.7, 0.2], "Bedroom AC (Refrigerant)": [-5.8, 1.5, -3.2], "Hall AC (Refrigerant)": [-5.3, 1.5, 2.0], "Kitchen Refrigerator": [2.0, 0.9, -0.35]}
        sc_coords = {"Bedroom": [-2.5, 0.8, -3.2], "Bathroom": [3.15, 0.8, -3.1], "Hall": [-2.5, 0.8, 2.0], "Kitchen": [3.75, 0.8, 1.25]}
        room_labels = [
            {"name": "🛋️ Hall", "x": -2.5, "y": 2.45, "z": 2.0, "watts": room_watts["Hall"], "temp": 27},
            {"name": "🛏️ Bedroom", "x": -2.5, "y": 2.45, "z": -3.2, "watts": room_watts["Bedroom"], "temp": 26},
            {"name": "🚿 Bath", "x": 3.15, "y": 2.45, "z": -3.1, "watts": room_watts["Bathroom"], "temp": 28},
            {"name": "🍳 Kitchen", "x": 3.75, "y": 2.45, "z": 1.25, "watts": room_watts["Kitchen"], "temp": kitchen_temp},
        ]
        payload = json.dumps({
            "items": scene_items, "rooms": room_labels, "lpg": lpg, "lpgStage": lpg_stage,
            "leakPos": leak_coords.get(leak_source, [4.1, 0.7, 0.2] if lpg >= LPG_MOD else None),
            "flame": flame, "smoke": smoke, "earthLeak": earth_leak, "scRoom": sc_room, "scPos": sc_coords.get(sc_room),
            "weather": weather, "floodCm": flood_cm, "floodCrit": FLOOD_CRIT,
            "valveOpen": st.session_state.circuits["LPG Solenoid Valve"], "mainOn": main_on, "totalWatts": total_watts, "currentA": current_a,
        })
        html_3d = """
        <div id="wrap" style="position:relative;width:100%;height:540px;border-radius:14px;overflow:hidden;border:1px solid rgba(56,189,248,0.4);background:#070d19;font-family:system-ui,sans-serif;">
          <div style="position:absolute;top:12px;left:12px;z-index:10;display:flex;gap:6px;flex-wrap:wrap;">
            <button onclick="setCam(11,12,13,0,0,0)" style="background:#1e293b;color:#e2e8f0;border:1px solid #38bdf8;padding:5px 10px;border-radius:8px;cursor:pointer;font-size:12px;">🏠 3D View</button>
            <button onclick="setCam(0,17,0.1,0,0,0)" style="background:#1e293b;color:#e2e8f0;border:1px solid #475569;padding:5px 10px;border-radius:8px;cursor:pointer;font-size:12px;">📐 Top Blueprint</button>
            <button onclick="setCam(-2.5,2.2,1.6,-2.5,1.15,4.78)" style="background:#1e293b;color:#e2e8f0;border:1px solid #a855f7;padding:5px 10px;border-radius:8px;cursor:pointer;font-size:12px;">📺 Watch TV</button>
            <button onclick="setCam(-2.5,6.5,-9,-2.5,0.5,-3.2)" style="background:#1e293b;color:#e2e8f0;border:1px solid #475569;padding:5px 10px;border-radius:8px;cursor:pointer;font-size:12px;">🛏️ Bedroom</button>
            <button onclick="setCam(9.5,6.5,6.5,3.7,0.5,1.2)" style="background:#1e293b;color:#e2e8f0;border:1px solid #475569;padding:5px 10px;border-radius:8px;cursor:pointer;font-size:12px;">🍳 Kitchen</button>
          </div>
          <div id="live-ticker" style="position:absolute;top:12px;right:12px;z-index:10;background:rgba(15,23,42,0.9);border:1px solid rgba(0,212,170,0.45);color:#e2e8f0;padding:8px 12px;border-radius:10px;font-size:12px;text-align:right;">
            <div style="color:#00d4aa;font-weight:700;">● LIVE 1BHK & SAFETY</div>
            <div id="tick-val">__TOTAL__ W • __AMPS__ A • 230 V</div>
          </div>
          <div id="inspector" style="position:absolute;bottom:12px;left:12px;z-index:10;background:rgba(15,23,42,0.92);border:1px solid rgba(56,189,248,0.4);color:#e2e8f0;padding:10px 14px;border-radius:10px;font-size:13px;max-width:390px;">
            <b>🖱️ Click or hover any device or sensor</b><br><span style="opacity:0.75;">Simulates 3-stage gas leaks, ELCB faults & Short-Circuit fire sparks</span>
          </div>
          <div id="labels-layer" style="position:absolute;inset:0;pointer-events:none;overflow:hidden;"></div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script>
        const DATA=__PAYLOAD__,wrap=document.getElementById("wrap"),inspector=document.getElementById("inspector"),labelsLayer=document.getElementById("labels-layer"),tickVal=document.getElementById("tick-val");
        const scene=new THREE.Scene(),isStorm=DATA.weather!=="Clear Sky";scene.background=new THREE.Color(isStorm?0x060b16:0x0c192c);
        const initW=wrap.clientWidth||720,camera=new THREE.PerspectiveCamera(45,initW/540,0.1,100),renderer=new THREE.WebGLRenderer({antialias:true});
        renderer.setSize(initW,540);wrap.appendChild(renderer.domElement);
        new ResizeObserver(()=>{const w=wrap.clientWidth;if(w>0){camera.aspect=w/540;camera.updateProjectionMatrix();renderer.setSize(w,540);}}).observe(wrap);
        const controls=new THREE.OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
        function saveCam(){try{localStorage.setItem("hg_cam_v1",JSON.stringify({px:camera.position.x,py:camera.position.y,pz:camera.position.z,tx:controls.target.x,ty:controls.target.y,tz:controls.target.z}));}catch(e){}}
        let restored=false;try{const s=JSON.parse(localStorage.getItem("hg_cam_v1"));if(s&&typeof s.px==="number"){camera.position.set(s.px,s.py,s.pz);controls.target.set(s.tx,s.ty,s.tz);controls.update();restored=true;}}catch(e){}
        if(!restored){camera.position.set(11,12,13);controls.target.set(0,0,0);controls.update();}
        controls.addEventListener("change",saveCam);
        window.setCam=(x,y,z,tx,ty,tz)=>{camera.position.set(x,y,z);controls.target.set(tx,ty,tz);controls.update();saveCam();};
        scene.add(new THREE.AmbientLight(0xffffff,isStorm?0.45:0.65));const sun=new THREE.DirectionalLight(0xffffff,isStorm?0.55:0.85);sun.position.set(8,16,10);scene.add(sun);
        function box(x,y,z,w,h,d,c,op=1){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color:c,transparent:op<1,opacity:op,roughness:0.72}));m.position.set(x,y,z);scene.add(m);return m;}
        box(0,-0.1,0,22,0.12,18,0x14532d);box(3.75,-0.03,6.8,2.0,0.06,3.6,0x64748b);
        [[-8.2,5.5],[-8.0,-5.0],[8.2,4.5],[7.8,-4.5]].forEach(([tx,tz])=>{const tr=new THREE.Mesh(new THREE.CylinderGeometry(0.18,0.22,1.0,8),new THREE.MeshStandardMaterial({color:0x78350f}));tr.position.set(tx,0.45,tz);const lv=new THREE.Mesh(new THREE.ConeGeometry(0.9,1.8,8),new THREE.MeshStandardMaterial({color:0x16a34a}));lv.position.set(tx,1.6,tz);scene.add(tr,lv);});
        box(-2.5,0,2.0,7.0,0.14,6.0,0x78553a);box(3.75,0,1.25,5.5,0.14,4.5,0x334155);box(3.75,-0.02,4.25,5.5,0.1,1.5,0x64748b);box(-2.5,0,-3.25,8.0,0.14,4.5,0x6b4c35);box(3.15,0,-3.1,3.3,0.14,4.2,0x0f766e);
        box(-2.5,1.05,-5.5,8.0,2.1,0.15,0xcbd5e1,0.55);box(3.15,1.05,-5.2,3.3,2.1,0.15,0xcbd5e1,0.55);box(-6.5,1.05,-3.25,0.15,2.1,4.5,0xcbd5e1,0.55);box(-6.0,1.05,2.0,0.15,2.1,6.0,0xcbd5e1,0.55);box(-2.5,1.05,5.0,7.0,2.1,0.15,0xcbd5e1,0.35);box(3.75,1.05,3.5,5.5,2.1,0.15,0xcbd5e1,0.35);box(6.5,1.05,1.25,0.15,2.1,4.5,0xcbd5e1,0.55);box(4.8,1.05,-3.1,0.15,2.1,4.2,0xcbd5e1,0.55);box(0.0,1.05,-1.0,13.0,2.1,0.12,0x94a3b8,0.5);box(1.0,1.05,2.0,0.12,2.1,6.0,0x94a3b8,0.5);box(1.5,1.05,-3.1,0.12,2.1,4.2,0x94a3b8,0.5);
        box(-4.0,0.25,-3.4,2.5,0.35,1.9,0x334155);box(-4.0,0.48,-3.4,2.35,0.15,1.75,0xf8fafc);box(-4.8,0.6,-3.85,0.4,0.12,0.6,0x38bdf8);box(-4.8,0.6,-2.95,0.4,0.12,0.6,0x38bdf8);
        box(-4.2,0.3,2.5,1.0,0.5,2.8,0x2563eb);box(-2.5,0.25,2.5,1.0,0.25,1.3,0x92400e);box(-2.5,0.3,4.7,2.2,0.45,0.45,0x1e293b);box(5.3,0.45,1.3,1.2,0.85,4.0,0x1f2937);box(5.3,0.9,2.5,0.8,0.08,1.1,0x0f172a);
        const burner=new THREE.Mesh(new THREE.TorusGeometry(0.18,0.03,8,20),new THREE.MeshStandardMaterial({color:DATA.valveOpen?0x38bdf8:0x1e293b,emissive:DATA.valveOpen?0x0284c7:0x000000,emissiveIntensity:DATA.valveOpen?0.9:0}));burner.rotation.x=Math.PI/2;burner.position.set(5.3,0.96,2.5);scene.add(burner);
        if(DATA.floodCm>0){const wh=0.04+(DATA.floodCm/40)*0.65;const w=new THREE.Mesh(new THREE.BoxGeometry(22,wh,18),new THREE.MeshStandardMaterial({color:DATA.floodCm>=DATA.floodCrit?0x0284c7:0x38bdf8,transparent:true,opacity:0.48}));w.position.set(0,wh/2-0.04,0);scene.add(w);}
        let rainGeo=null;if(isStorm){const pts=[];for(let i=0;i<(DATA.weather==="Severe Flood"?450:250);i++)pts.push((Math.random()-0.5)*20,Math.random()*10,(Math.random()-0.5)*16);rainGeo=new THREE.BufferGeometry();rainGeo.setAttribute("position",new THREE.Float32BufferAttribute(pts,3));scene.add(new THREE.Points(rainGeo,new THREE.PointsMaterial({color:0x7dd3fc,size:0.11,transparent:true,opacity:0.75})));}
        let gasGeo=null,gasOrigin=null;if(DATA.leakPos&&DATA.lpgStage!=="SAFE"){gasOrigin=DATA.leakPos;const pts=[];for(let i=0;i<65;i++)pts.push(gasOrigin[0]+(Math.random()-0.5)*0.6,gasOrigin[1]+Math.random()*0.6,gasOrigin[2]+(Math.random()-0.5)*0.6);gasGeo=new THREE.BufferGeometry();gasGeo.setAttribute("position",new THREE.Float32BufferAttribute(pts,3));scene.add(new THREE.Points(gasGeo,new THREE.PointsMaterial({color:DATA.lpgStage==="CRITICAL"?0xef4444:0xf59e0b,size:0.22,transparent:true,opacity:0.65})));}
        let sparkGeo=null,sparkOrigin=null,sparkLight=null;if(DATA.scPos){sparkOrigin=DATA.scPos;const pts=[];for(let i=0;i<70;i++)pts.push(sparkOrigin[0],sparkOrigin[1],sparkOrigin[2]);sparkGeo=new THREE.BufferGeometry();sparkGeo.setAttribute("position",new THREE.Float32BufferAttribute(pts,3));scene.add(new THREE.Points(sparkGeo,new THREE.PointsMaterial({color:0xfacc15,size:0.14,transparent:true,opacity:0.95})));sparkLight=new THREE.PointLight(0xff5500,2.5,6);sparkLight.position.set(sparkOrigin[0],sparkOrigin[1]+0.4,sparkOrigin[2]);scene.add(sparkLight);}
        const interactables=[];
        function addSensor(x,y,z,c,active,title,room,detail){const m=new THREE.Mesh(new THREE.OctahedronGeometry(0.24,0),new THREE.MeshStandardMaterial({color:active?0xef4444:c,emissive:active?0xdc2626:c,emissiveIntensity:active?0.9:0.3}));m.position.set(x,y,z);m.userData={title,room,detail,power:active?"⚠️ TRIGGERED":"Monitoring"};scene.add(m);interactables.push(m);}
        const cyl=new THREE.Mesh(new THREE.CylinderGeometry(0.3,0.3,0.85,18),new THREE.MeshStandardMaterial({color:DATA.lpgStage==="CRITICAL"?0xef4444:0xdc2626}));cyl.position.set(4.1,0.48,0.2);cyl.userData={title:"LPG Cylinder & Gas Sensor",room:"Kitchen",detail:`${DATA.lpg} ppm (${DATA.lpgStage}) • Valve: ${DATA.valveOpen?"OPEN":"SHUT"}`,power:DATA.lpgStage};scene.add(cyl);interactables.push(cyl);
        addSensor(5.3,1.45,2.5,0xf97316,DATA.flame,"IR Flame Sensor","Kitchen",DATA.flame?"FLAME DETECTED!":"Clear");
        addSensor(0.8,2.05,0.5,0xa855f7,DATA.smoke,"Optical Smoke Sensor","Hall / Kitchen",DATA.smoke?"SMOKE DETECTED!":"Clear");
        addSensor(3.75,0.25,4.4,0x38bdf8,DATA.floodCm>=DATA.floodCrit,"Flood Water Sensor","Porch",`${DATA.floodCm} cm`);
        addSensor(-5.5,1.8,0.2,0xeab308,DATA.earthLeak||DATA.scRoom!=="None","ELCB / Earth Leakage Sensor","Main Panel",DATA.earthLeak?"LEAKAGE >30mA!":"Normal");
        const tvCanvas=document.createElement("canvas");tvCanvas.width=256;tvCanvas.height=144;const tvCtx=tvCanvas.getContext("2d"),tvTex=new THREE.CanvasTexture(tvCanvas);let tvIsOn=false;
        function drawCartoon(t){tvCtx.fillStyle="#38bdf8";tvCtx.fillRect(0,0,256,144);tvCtx.fillStyle="#fde047";tvCtx.beginPath();tvCtx.arc(210,32,16+Math.sin(t*2)*2,0,Math.PI*2);tvCtx.fill();const cx=((t*22)%300)-30;tvCtx.fillStyle="#fff";tvCtx.beginPath();tvCtx.arc(cx,35,12,0,Math.PI*2);tvCtx.arc(cx+14,32,15,0,Math.PI*2);tvCtx.arc(cx+28,36,11,0,Math.PI*2);tvCtx.fill();tvCtx.fillStyle="#22c55e";tvCtx.fillRect(0,102,256,42);const bx=60+Math.sin(t*1.2)*40+40,by=88-Math.abs(Math.sin(t*3.2))*28;tvCtx.fillStyle="#f97316";tvCtx.beginPath();tvCtx.arc(bx,by,18,0,Math.PI*2);tvCtx.fill();tvCtx.fillStyle="#0f172a";tvCtx.beginPath();tvCtx.arc(bx-6,by-4,2.5,0,Math.PI*2);tvCtx.arc(bx+6,by-4,2.5,0,Math.PI*2);tvCtx.fill();tvCtx.beginPath();tvCtx.arc(bx,by+2,7,0,Math.PI);tvCtx.stroke();tvCtx.fillStyle="rgba(15,23,42,0.75)";tvCtx.fillRect(8,8,92,18);tvCtx.fillStyle="#facc15";tvCtx.font="bold 10px sans-serif";tvCtx.fillText("📺 TOON TV",14,20);tvTex.needsUpdate=true;}
        const spinners=[],acStreams=[],chimneyStreams=[],pulseLEDs=[];
        DATA.items.forEach(item=>{
            const c=!item.on?0x475569:item.type==="geyser"?0xf97316:item.type==="ac"?0x38bdf8:item.type==="tv"?0x0f172a:item.type==="fridge"?0xe2e8f0:(item.type==="fan"||item.type==="chimney")?0x22c55e:0xfef08a;
            let mesh;const mat=new THREE.MeshStandardMaterial({color:c,emissive:item.on&&item.type!=="tv"&&item.type!=="fridge"?c:0x000000,emissiveIntensity:item.on?0.5:0});
            if(item.type==="fan"){const g=new THREE.Group(),h=new THREE.Mesh(new THREE.CylinderGeometry(0.14,0.14,0.12,12),mat);g.add(h,new THREE.Mesh(new THREE.BoxGeometry(1.1,0.04,0.14),mat),new THREE.Mesh(new THREE.BoxGeometry(0.14,0.04,1.1),mat));g.position.set(item.pos[0],item.pos[1],item.pos[2]);scene.add(g);mesh=h;if(item.on)spinners.push(g);}
            else if(item.type==="ac"){mesh=new THREE.Mesh(new THREE.BoxGeometry(0.28,0.35,1.2),mat);mesh.position.set(item.pos[0],item.pos[1],item.pos[2]);scene.add(mesh);if(item.on){const pts=[];for(let i=0;i<28;i++)pts.push(item.pos[0]+0.2+Math.random()*1.4,item.pos[1]-0.1-Math.random()*0.8,item.pos[2]+(Math.random()-0.5)*1.0);const geo=new THREE.BufferGeometry();geo.setAttribute("position",new THREE.Float32BufferAttribute(pts,3));scene.add(new THREE.Points(geo,new THREE.PointsMaterial({color:0x67e8f9,size:0.08,transparent:true,opacity:0.8})));acStreams.push({geo,originX:item.pos[0]+0.2,originY:item.pos[1]-0.1});}}
            else if(item.type==="geyser"){mesh=new THREE.Mesh(new THREE.CylinderGeometry(0.26,0.26,0.75,14),new THREE.MeshStandardMaterial({color:0xe2e8f0,roughness:0.4}));mesh.position.set(item.pos[0],item.pos[1],item.pos[2]);scene.add(mesh);const lm=new THREE.MeshStandardMaterial({color:item.on?0xff4500:0x334155,emissive:item.on?0xff4500:0x000000,emissiveIntensity:item.on?1.2:0});const led=new THREE.Mesh(new THREE.SphereGeometry(0.075,10,10),lm);led.position.set(item.pos[0]-0.27,item.pos[1]+0.1,item.pos[2]);scene.add(led);if(item.on)pulseLEDs.push(lm);}
            else if(item.type==="fridge"){mesh=new THREE.Mesh(new THREE.BoxGeometry(0.85,1.45,0.8),mat);mesh.position.set(item.pos[0],item.pos[1],item.pos[2]);scene.add(mesh);}
            else if(item.type==="tv"){mesh=new THREE.Mesh(new THREE.BoxGeometry(1.55,0.9,0.08),mat);mesh.position.set(item.pos[0],item.pos[1],item.pos[2]);scene.add(mesh);tvIsOn=item.on;const scr=new THREE.Mesh(new THREE.PlaneGeometry(1.42,0.78),item.on?new THREE.MeshBasicMaterial({map:tvTex,side:THREE.DoubleSide}):new THREE.MeshBasicMaterial({color:0x090d16,side:THREE.DoubleSide}));scr.position.set(item.pos[0],item.pos[1],item.pos[2]-0.05);scr.rotation.y=Math.PI;scene.add(scr);}
            else if(item.type==="chimney"){mesh=new THREE.Mesh(new THREE.ConeGeometry(0.45,0.55,4),mat);mesh.position.set(item.pos[0],item.pos[1],item.pos[2]);scene.add(mesh);if(item.on){const pts=[];for(let i=0;i<20;i++)pts.push(item.pos[0]+(Math.random()-0.5)*0.5,item.pos[1]-0.8+Math.random()*0.7,item.pos[2]+(Math.random()-0.5)*0.5);const geo=new THREE.BufferGeometry();geo.setAttribute("position",new THREE.Float32BufferAttribute(pts,3));scene.add(new THREE.Points(geo,new THREE.PointsMaterial({color:0xa7f3d0,size:0.07,transparent:true,opacity:0.7})));chimneyStreams.push({geo,baseY:item.pos[1]-0.8,topY:item.pos[1]-0.1});}}
            else{mesh=new THREE.Mesh(item.type==="tube"?new THREE.BoxGeometry(1.3,0.1,0.1):new THREE.SphereGeometry(0.18,12,12),mat);mesh.position.set(item.pos[0],item.pos[1],item.pos[2]);scene.add(mesh);if(item.on&&(item.type==="tube"||item.type==="bulb")){const pl=new THREE.PointLight(0xfef9c3,0.65,5.5);pl.position.set(item.pos[0],item.pos[1]-0.2,item.pos[2]);scene.add(pl);}}
            mesh.userData={title:item.name,room:item.room,detail:item.on?`ACTIVE • ${item.watts} W (${item.amps} A)`:"OFF / TRIPPED",power:item.on?`Est. ₹${((item.watts/1000)*7).toFixed(2)}/hr`:"Idle"};interactables.push(mesh);
        });
        const labelEls=DATA.rooms.map(r=>{const el=document.createElement("div");el.style.cssText="position:absolute;transform:translate(-50%,-50%);background:rgba(15,23,42,0.88);border:1px solid rgba(56,189,248,0.45);color:#f8fafc;padding:3px 7px;border-radius:7px;font-size:10.5px;white-space:nowrap;";el.innerHTML=`<b>${r.name}</b> • <span style="color:#00d4aa;">${r.watts}W</span> • ${r.temp}°C`;labelsLayer.appendChild(el);return{el,pos:new THREE.Vector3(r.x,r.y,r.z)};});
        const raycaster=new THREE.Raycaster(),mouse=new THREE.Vector2();
        function inspectAt(e){const r=renderer.domElement.getBoundingClientRect();mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;raycaster.setFromCamera(mouse,camera);const h=raycaster.intersectObjects(interactables);if(h.length){const d=h[0].object.userData;inspector.innerHTML=`<b>${d.room} • ${d.title}</b><br><span style="color:#38bdf8;">${d.detail}</span> • ${d.power}`;}}
        wrap.addEventListener("mousemove",inspectAt);wrap.addEventListener("click",inspectAt);
        setInterval(()=>{const v=DATA.mainOn?(229+Math.floor(Math.random()*3)):0;tickVal.textContent=`${DATA.totalWatts} W • ${DATA.currentA} A • ${v} V`;},1500);
        let clockT=0;
        function animate(){
            requestAnimationFrame(animate);clockT+=0.04;if(tvIsOn)drawCartoon(clockT);spinners.forEach(f=>f.rotation.y+=0.14);
            acStreams.forEach(s=>{const a=s.geo.attributes.position.array;for(let i=0;i<a.length;i+=3){a[i]+=0.035;a[i+1]-=0.015;if(a[i]>s.originX+1.6){a[i]=s.originX;a[i+1]=s.originY;}}s.geo.attributes.position.needsUpdate=true;});
            chimneyStreams.forEach(s=>{const a=s.geo.attributes.position.array;for(let i=1;i<a.length;i+=3){a[i]+=0.025;if(a[i]>s.topY)a[i]=s.baseY;}s.geo.attributes.position.needsUpdate=true;});
            pulseLEDs.forEach(m=>{m.emissiveIntensity=0.8+Math.sin(clockT*3)*0.5;});
            if(gasGeo){const a=gasGeo.attributes.position.array;for(let i=0;i<a.length;i+=3){a[i]+=(Math.random()-0.5)*0.04;a[i+1]+=0.02;a[i+2]+=(Math.random()-0.5)*0.04;if(a[i+1]>gasOrigin[1]+1.5){a[i]=gasOrigin[0]+(Math.random()-0.5)*0.4;a[i+1]=gasOrigin[1];a[i+2]=gasOrigin[2]+(Math.random()-0.5)*0.4;}}gasGeo.attributes.position.needsUpdate=true;}
            if(sparkGeo){const a=sparkGeo.attributes.position.array;for(let i=0;i<a.length;i+=3){a[i]+=(Math.random()-0.5)*0.18;a[i+1]+=Math.random()*0.12-0.03;a[i+2]+=(Math.random()-0.5)*0.18;if(Math.random()<0.12){a[i]=sparkOrigin[0];a[i+1]=sparkOrigin[1];a[i+2]=sparkOrigin[2];}}sparkGeo.attributes.position.needsUpdate=true;if(sparkLight)sparkLight.intensity=1.5+Math.random()*3.0;}
            if(rainGeo){const a=rainGeo.attributes.position.array;for(let i=1;i<a.length;i+=3){a[i]-=0.22;if(a[i]<0)a[i]=10;}rainGeo.attributes.position.needsUpdate=true;}
            controls.update();const w=wrap.clientWidth;if(w>0)labelEls.forEach(it=>{const p=it.pos.clone().project(camera);if(p.z<1){it.el.style.display="block";it.el.style.left=((p.x*0.5+0.5)*w)+"px";it.el.style.top=((-p.y*0.5+0.5)*540)+"px";}else it.el.style.display="none";});
            renderer.render(scene,camera);
        }
        animate();
        </script>
        """.replace("__PAYLOAD__", payload).replace("__TOTAL__", str(total_watts)).replace("__AMPS__", str(current_a))
        components.html(html_3d, height=555)

elif page == "📊 Overview":
    st.progress(risk_score / 100, text=f"Overall Residential Hazard Risk: {risk_score}%")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Gas Level", f"{lpg} ppm", f"Stage: {lpg_stage}", delta_color="inverse" if lpg_stage != "SAFE" else "normal")
    k2.metric("Kitchen Temp", f"{kitchen_temp} °C", f"Stage: {temp_stage}", delta_color="inverse" if temp_stage != "SAFE" else "normal")
    k3.metric("Flood Water", f"{flood_cm} cm", f"Stage: {flood_stage}", delta_color="inverse" if flood_stage != "SAFE" else "normal")
    k4.metric("1BHK Live Load", f"{total_watts} W", f"{current_a} A")

elif page == "⚡ Power":
    st.subheader("⚡ Room-by-Room Power Consumption")
    st.bar_chart(pd.DataFrame({"Room": list(room_watts.keys()), "Power (W)": list(room_watts.values())}), x="Room", y="Power (W)", color="#00D4AA")
    st.area_chart(pd.DataFrame(st.session_state.history), x="Time", y="Power (W)", color="#38BDF8")

elif page == "🔌 Controls":
    st.subheader("🔌 Master Interlock Controls")
    c1, c2 = st.columns(2)
    with c1: st.session_state.circuits["Main Breaker"] = st.toggle("Main Breaker (ELCB/MCB)", value=st.session_state.circuits["Main Breaker"])
    with c2: st.session_state.circuits["LPG Solenoid Valve"] = st.toggle("LPG Solenoid Valve", value=st.session_state.circuits["LPG Solenoid Valve"])
    if st.button("🔄 Restore All Interlocks"):
        if crit_reasons: st.warning("Clear all CRITICAL hazards / Short Circuits in the sidebar before restoring.")
        else: st.session_state.circuits["Main Breaker"] = True; st.session_state.circuits["LPG Solenoid Valve"] = True; st.rerun()

elif page == "🚨 Emergency":
    st.subheader("🚨 Owner & Client Emergency Response")
    col_c, col_h = st.columns(2)
    with col_c:
        st.markdown("**🏠 Registered Owner & Client Details**")
        st.session_state.client["name"] = st.text_input("House Owner & Client", st.session_state.client["name"])
        st.session_state.client["address"] = st.text_input("Residential Address", st.session_state.client["address"])
        st.session_state.client["phone"] = st.text_input("Owner Mobile (Rishi)", st.session_state.client["phone"])
        st.session_state.client["family"] = st.text_input("Emergency Family Contact", st.session_state.client["family"])
    with col_h:
        st.markdown("**📞 24×7 Emergency Contacts (Telangana / India)**")
        st.markdown(
            f"- **House Owner ({st.session_state.client['name']}):** [`{st.session_state.client['phone']}`](tel:{st.session_state.client['phone']})\n"
            f"- **Emergency Family Contact:** [`{st.session_state.client['family']}`](tel:{st.session_state.client['family']})\n"
            f"- **National Emergency (Police/Fire/Medical):** [`112`](tel:112)\n"
            f"- **Fire Brigade:** [`101`](tel:101)\n"
            f"- **Emergency Ambulance:** [`108`](tel:108)\n"
            f"- **LPG Gas Leakage Helpline:** [`1906`](tel:1906)\n"
            f"- **TGSPDCL Electricity / Shock Fault:** [`1912`](tel:1912)"
        )
    sos_msg = f"SOS ALERT | Owner: {st.session_state.client['name']} ({st.session_state.client['phone']}) | Location: {st.session_state.client['address']} | Hazards: {', '.join(crit_reasons) if crit_reasons else 'Manual Test'} | Gas: {lpg} ppm | Temp: {kitchen_temp}°C | Flood: {flood_cm} cm"
    if st.button("🚨 Dispatch Emergency SOS Alert", type="primary"):
        st.session_state.logs.insert(0, {"Time": datetime.now().strftime("%I:%M:%S %p"), "Event": "SOS DISPATCHED", "Action": sos_msg})
        st.error(f"Emergency SOS Logged & Ready:\n\n`{sos_msg}`")

elif page == "📼 Black Box":
    hist_df = pd.DataFrame(st.session_state.history)
    st.dataframe(hist_df, use_container_width=True)
    st.download_button("⬇️ Download Black Box CSV", data=hist_df.to_csv(index=False).encode("utf-8"), file_name="rishi_home_guardian_log.csv", mime="text/csv")
    if st.session_state.logs:
        st.subheader("🚨 Interlock & SOS Events")
        st.dataframe(pd.DataFrame(st.session_state.logs), use_container_width=True)
