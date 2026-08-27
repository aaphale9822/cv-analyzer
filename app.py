import streamlit as st
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
import io

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="CV Capacity Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design & Mobile Styling
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .metric-title {
        font-size: 0.875rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #38bdf8;
        margin-top: 0.25rem;
    }
    .metric-value-sub {
        font-size: 1.6rem;
        font-weight: 700;
        color: #10b981;
        margin-top: 0.25rem;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.5rem;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to update HSV preset values in session state
def update_hsv_presets():
    preset = st.session_state.color_preset
    if preset == "Blue":
        st.session_state.hue_min = 85
        st.session_state.hue_max = 135
        st.session_state.sat_min = 50
        st.session_state.sat_max = 255
        st.session_state.val_min = 20
        st.session_state.val_max = 255
    elif preset == "Red":
        st.session_state.hue_min = 0
        st.session_state.hue_max = 15
        st.session_state.sat_min = 50
        st.session_state.sat_max = 255
        st.session_state.val_min = 20
        st.session_state.val_max = 255
    elif preset == "Green":
        st.session_state.hue_min = 35
        st.session_state.hue_max = 85
        st.session_state.sat_min = 50
        st.session_state.sat_max = 255
        st.session_state.val_min = 20
        st.session_state.val_max = 255
    elif preset == "Black/Dark":
        st.session_state.hue_min = 0
        st.session_state.hue_max = 179
        st.session_state.sat_min = 0
        st.session_state.sat_max = 255
        st.session_state.val_min = 0
        st.session_state.val_max = 90

# Title and App Info
st.title("⚡ Cyclic Voltammetry (CV) Capacity & Capacitance Analyzer")
st.markdown("""
Extract CV curve coordinates from photos, calibrate physical units dynamically, and calculate specific capacity and capacitance.
""")

# Setup Sidebar - Step 1: Input Source
st.sidebar.header("📁 Step 1: Input Source")
input_option = st.sidebar.radio("Select Image Source", ["Upload Photo", "Camera Capture", "Load Sample CV Graph"])

# Load image based on selection
uploaded_file = None
camera_file = None
image_pil = None

if input_option == "Upload Photo":
    uploaded_file = st.sidebar.file_uploader("Upload Graph Image", type=["png", "jpg", "jpeg"])
elif input_option == "Camera Capture":
    camera_file = st.sidebar.camera_input("Take a photo of the graph screen")
else:
    try:
        image_pil = Image.open("assets/sample_cv_plot.png")
    except Exception as e:
        st.sidebar.error("Failed to load sample image. Please upload an image.")

if uploaded_file is not None:
    image_pil = Image.open(uploaded_file)
elif camera_file is not None:
    image_pil = Image.open(camera_file)

if image_pil is not None:
    image_pil = ImageOps.exif_transpose(image_pil)

# Setup Sidebar - Step 2: Unit Configuration Expander
st.sidebar.header("⚙️ Step 2: Unit Settings")
with st.sidebar.expander("Configure Units", expanded=True):
    potential_unit = st.selectbox("Potential Unit (X-axis)", ["V", "mV"])
    is_normalized = st.checkbox("Is Y-axis already mass-normalized in the plot?", value=True)
    if is_normalized:
        current_unit = st.selectbox("Current Unit (Y-axis)", ["A/g", "mA/g"])
    else:
        current_unit = st.selectbox("Current Unit (Y-axis)", ["A", "mA", "uA"])
    
    scan_rate_unit = st.selectbox("Scan Rate Unit", ["mV/s", "V/s", "uV/s"])
    capacity_unit = st.selectbox("Output Capacity Unit", ["mAh/g", "Ah/g", "C/g", "mAh"])
    capacitance_unit = st.selectbox("Output Capacitance Unit", ["F/g", "mF/g", "F/cm²"])

# Setup Sidebar - Step 3: Mass Configuration (Zn//MnO2 cell normalization)
st.sidebar.header("⚖️ Step 3: Mass Configuration")
m_basis_toggle = st.sidebar.selectbox(
    "Mass Normalization Basis",
    ["Cathode Mass Only", "Total Mass (Cathode + Anode)"],
    index=0
)

m_cathode = st.sidebar.number_input("Cathode Active Mass (mg)", value=8.8, min_value=0.001, step=0.1, format="%.3f")
m_anode = st.sidebar.number_input("Anode Active Mass (mg)", value=0.0, min_value=0.0, step=0.1, format="%.3f")

if m_basis_toggle == "Cathode Mass Only":
    m_basis = m_cathode
else:
    m_basis = m_cathode + m_anode
    if m_basis <= 0.0:
        st.sidebar.error("🚨 Total active mass must be greater than 0 mg.")
        st.stop()

if is_normalized:
    m_original = st.sidebar.number_input("Original Mass Setting in Plot Software (mg)", value=10.0, min_value=0.001, step=0.1, format="%.3f")

# Dynamic display of Electrode Area input if capacitance unit is F/cm²
if capacitance_unit == "F/cm²":
    electrode_area = st.sidebar.number_input("Electrode Area (cm²)", value=1.0, min_value=0.001, step=0.1, format="%.3f")

# Sidebar - Step 4: Calibration Margins
st.sidebar.header("📏 Step 4: Calibration Crop Margins")
crop_left = st.sidebar.slider("Left Margin (%)", 0, 90, 15)
crop_right = st.sidebar.slider("Right Margin (%)", 0, 90, 5)
crop_top = st.sidebar.slider("Top Margin (%)", 0, 90, 8)
crop_bottom = st.sidebar.slider("Bottom Margin (%)", 0, 90, 12)

if crop_left + crop_right >= 100 or crop_top + crop_bottom >= 100:
    st.sidebar.error("🚨 Total margins exceed 100%. Please reduce crop margins.")
    st.stop()

# Sidebar - Step 5: Physical Calibration Bounds & Values
st.sidebar.header("🏷️ Step 5: Axis Calibration Limits")

# Handle smart value persistence & scaling when units change
if "prev_potential_unit" not in st.session_state:
    st.session_state.prev_potential_unit = potential_unit
    st.session_state.v_start = 0.0
    st.session_state.v_end = 1.0 if input_option == "Load Sample CV Graph" else 1.8

if potential_unit != st.session_state.prev_potential_unit:
    if potential_unit == "mV" and st.session_state.prev_potential_unit == "V":
        st.session_state.v_start *= 1000.0
        st.session_state.v_end *= 1000.0
    elif potential_unit == "V" and st.session_state.prev_potential_unit == "mV":
        st.session_state.v_start /= 1000.0
        st.session_state.v_end /= 1000.0
    st.session_state.prev_potential_unit = potential_unit

if "prev_current_unit" not in st.session_state:
    st.session_state.prev_current_unit = current_unit
    st.session_state.i_min = -1.0 if input_option == "Load Sample CV Graph" else -0.07
    st.session_state.i_max = 1.0 if input_option == "Load Sample CV Graph" else 0.085

# Convert values if current unit changed
if current_unit != st.session_state.prev_current_unit:
    units_to_base = {"A/g": 1.0, "mA/g": 1e-3, "A": 1.0, "mA": 1e-3, "uA": 1e-6}
    curr_factor_prev = units_to_base.get(st.session_state.prev_current_unit, 1.0)
    curr_factor_new = units_to_base.get(current_unit, 1.0)
    
    st.session_state.i_min = st.session_state.i_min * curr_factor_prev / curr_factor_new
    st.session_state.i_max = st.session_state.i_max * curr_factor_prev / curr_factor_new
    st.session_state.prev_current_unit = current_unit

# Draw Sidebar Calibration Inputs
col_v1, col_v2 = st.sidebar.columns(2)
with col_v1:
    v_start = st.number_input(f"Start Potential ({potential_unit})", value=st.session_state.v_start, step=0.1, key="v_start_val")
with col_v2:
    v_end = st.number_input(f"End Potential ({potential_unit})", value=st.session_state.v_end, step=0.1, key="v_end_val")
st.session_state.v_start = v_start
st.session_state.v_end = v_end

col_i1, col_i2 = st.sidebar.columns(2)
with col_i1:
    i_min = st.number_input(f"Min Current ({current_unit})", value=st.session_state.i_min, step=0.01, format="%.4f", key="i_min_val")
with col_i2:
    i_max = st.number_input(f"Max Current ({current_unit})", value=st.session_state.i_max, step=0.01, format="%.4f", key="i_max_val")
st.session_state.i_min = i_min
st.session_state.i_max = i_max

# Sidebar - Step 6: Measurement Settings
st.sidebar.header("⏱️ Step 6: Scan Rate")
scan_rate_val = st.sidebar.number_input(f"Scan Rate ({scan_rate_unit})", value=0.1 if scan_rate_unit == "mV/s" else 0.0001, min_value=0.000001, format="%.6f")

# Sidebar - Step 7: Color Segmentation Settings
st.sidebar.header("🎨 Step 7: Curve Color Extraction")
st.sidebar.selectbox("Color Preset", ["Blue", "Red", "Green", "Black/Dark", "Custom"], key="color_preset", on_change=update_hsv_presets)

# Initialize Session State values for HSV if empty
if "hue_min" not in st.session_state:
    st.session_state.hue_min = 85
if "hue_max" not in st.session_state:
    st.session_state.hue_max = 135
if "sat_min" not in st.session_state:
    st.session_state.sat_min = 50
if "sat_max" not in st.session_state:
    st.session_state.sat_max = 255
if "val_min" not in st.session_state:
    st.session_state.val_min = 20
if "val_max" not in st.session_state:
    st.session_state.val_max = 255

hue_min = st.sidebar.slider("Hue Min", 0, 179, key="hue_min")
hue_max = st.sidebar.slider("Hue Max", 0, 179, key="hue_max")
sat_min = st.sidebar.slider("Sat Min", 0, 255, key="sat_min")
sat_max = st.sidebar.slider("Sat Max", 0, 255, key="sat_max")
val_min = st.sidebar.slider("Val Min", 0, 255, key="val_min")
val_max = st.sidebar.slider("Val Max", 0, 255, key="val_max")

# Helper function to generate red color mask handling wrapping
def apply_hsv_mask(hsv_img, h_min, h_max, s_min, s_max, v_min, v_max, preset):
    if preset == "Red":
        mask1 = cv2.inRange(hsv_img, np.array([0, s_min, v_min]), np.array([h_max, s_max, v_max]))
        mask2 = cv2.inRange(hsv_img, np.array([180 - h_max if h_max > 0 else 165, s_min, v_min]), np.array([179, s_max, v_max]))
        return cv2.bitwise_or(mask1, mask2)
    else:
        return cv2.inRange(hsv_img, np.array([h_min, s_min, v_min]), np.array([h_max, s_max, v_max]))

# Main Panel layout
if image_pil is None:
    st.info("👋 Welcome! Please upload a photo, take a picture, or load the sample CV graph in the sidebar to start.")
    st.image("assets/sample_cv_plot.png", caption="Sample CV Plot", use_container_width=True)
else:
    img_bgr = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    h, w, _ = img_bgr.shape
    
    # Calculate bounding box coordinates
    x1 = int(w * (crop_left / 100.0))
    x2 = int(w * (1.0 - crop_right / 100.0))
    y1 = int(h * (crop_top / 100.0))
    y2 = int(h * (1.0 - crop_bottom / 100.0))
    
    # Draw Calibration Bounding Box
    img_calibrated = img_bgr.copy()
    cv2.rectangle(img_calibrated, (x1, y1), (x2, y2), (0, 0, 255), 3)
    
    # Bounding Box label text formatting
    f_scale = max(0.4, min(w, h) / 900.0)
    thickness = max(1, int(min(w, h) / 450.0))
    color_lbl = (0, 0, 255)
    
    cv2.putText(img_calibrated, f"I_max: {i_max:.3f}", (max(5, x1 - int(100*f_scale)), y1 + int(10*f_scale)), cv2.FONT_HERSHEY_SIMPLEX, f_scale, color_lbl, thickness)
    cv2.putText(img_calibrated, f"I_min: {i_min:.3f}", (max(5, x1 - int(100*f_scale)), y2 - int(10*f_scale)), cv2.FONT_HERSHEY_SIMPLEX, f_scale, color_lbl, thickness)
    cv2.putText(img_calibrated, f"V_start: {v_start:.2f}", (x1, min(h - 5, y2 + int(25*f_scale))), cv2.FONT_HERSHEY_SIMPLEX, f_scale, color_lbl, thickness)
    cv2.putText(img_calibrated, f"V_end: {v_end:.2f}", (max(0, x2 - int(100*f_scale)), min(h - 5, y2 + int(25*f_scale))), cv2.FONT_HERSHEY_SIMPLEX, f_scale, color_lbl, thickness)
    
    img_calibrated_rgb = cv2.cvtColor(img_calibrated, cv2.COLOR_BGR2RGB)
    
    # Color masking
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = apply_hsv_mask(hsv, hue_min, hue_max, sat_min, sat_max, val_min, val_max, st.session_state.color_preset)
    
    # Restrict mask inside bounding box
    cropped_mask = np.zeros_like(mask)
    cropped_mask[y1:y2, x1:x2] = mask[y1:y2, x1:x2]
    
    y_idx, x_idx = np.where(cropped_mask > 0)
    
    # Render tabs
    tab_cal, tab_anal = st.tabs(["🎯 Calibration & HSV Mask", "📈 Analytical Capacity & Capacitance"])
    
    with tab_cal:
        st.subheader("Image Preprocessing Visualizer")
        st.caption(f"Red boundary defines bounds corresponding to calibration: Potential [{v_start} to {v_end}] {potential_unit} and Current [{i_min} to {i_max}] {current_unit}.")
        col_img1, col_img2 = st.columns(2)
        with col_img1:
            st.image(img_calibrated_rgb, caption="Graph Calibration Boundary Box Overlay", use_container_width=True)
        with col_img2:
            st.image(cropped_mask, caption="Isolated Color Mask (inside box)", use_container_width=True, clamp=True)
            
    with tab_anal:
        if len(x_idx) < 10:
            st.warning("⚠️ Insufficient pixels detected in the crop region. Please adjust HSV sliders to isolate your CV curve line.")
        else:
            # Conversion factors to standard SI units
            potential_factors = {"V": 1.0, "mV": 1e-3}
            current_factors = {"A/g": 1.0, "mA/g": 1e-3, "A": 1.0, "mA": 1e-3, "uA": 1e-6}
            scan_rate_factors = {"mV/s": 1e-3, "V/s": 1.0, "uV/s": 1e-6}
            
            factor_V = potential_factors[potential_unit]
            factor_I = current_factors[current_unit]
            factor_v = scan_rate_factors[scan_rate_unit]
            
            # Map pixels to user units
            x_rel = (x_idx - x1) / (x2 - x1)
            y_rel = (y_idx - y1) / (y2 - y1)
            
            V_user = v_start + x_rel * (v_end - v_start)
            I_user = i_max - y_rel * (i_max - i_min)
            
            # Convert user values to standard SI values (Potential in Volts, Current in A or A/g)
            V_si = V_user * factor_V
            I_si = I_user * factor_I
            scan_rate_si = scan_rate_val * factor_v
            
            # Derive raw current in Amperes
            if is_normalized:
                I_raw_A = I_si * (m_original / 1000.0)
            else:
                I_raw_A = I_si
                
            # Perform Voltage Binning in SI
            num_bins = 200
            v_start_si = v_start * factor_V
            v_end_si = v_end * factor_V
            v_min_si = min(v_start_si, v_end_si)
            v_max_si = max(v_start_si, v_end_si)
            
            voltage_bins_si = np.linspace(v_min_si, v_max_si, num_bins)
            bin_width_si = (v_max_si - v_min_si) / (num_bins - 1)
            
            bin_idx = np.round((V_si - v_min_si) / (v_max_si - v_min_si) * (num_bins - 1)).astype(int)
            bin_idx = np.clip(bin_idx, 0, num_bins - 1)
            
            upper_raw_A = np.full(num_bins, np.nan)
            lower_raw_A = np.full(num_bins, np.nan)
            
            for b in range(num_bins):
                in_bin = (bin_idx == b)
                if np.any(in_bin):
                    curr_in_bin = I_raw_A[in_bin]
                    upper_raw_A[b] = np.max(curr_in_bin)
                    lower_raw_A[b] = np.min(curr_in_bin)
                    
            # Interpolation
            valid_upper = ~np.isnan(upper_raw_A)
            valid_lower = ~np.isnan(lower_raw_A)
            
            if np.sum(valid_upper) > 2 and np.sum(valid_lower) > 2:
                upper_curve_raw_A = np.interp(voltage_bins_si, voltage_bins_si[valid_upper], upper_raw_A[valid_upper])
                lower_curve_raw_A = np.interp(voltage_bins_si, voltage_bins_si[valid_lower], lower_raw_A[valid_lower])
                
                # Separation of CV Loop into Charge and Discharge branches
                # Charge branch is top half clipped to I > 0
                # Discharge branch is bottom half clipped to I < 0
                charge_branch_si = np.maximum(upper_curve_raw_A, 0.0)
                discharge_branch_si = np.minimum(lower_curve_raw_A, 0.0)
                
               
        # Math integration (Raw Area in Watts = A * V)
                area_discharge = np.abs(np.trapezoid(discharge_branch_si, x=voltage_bins_si))
                area_charge = np.abs(np.trapezoid(charge_branch_si, x=voltage_bins_si))
                
                # Absolute charge Q (C = A * s)
                q_discharge_abs = area_discharge / scan_rate_si
                q_charge_abs = area_charge / scan_rate_si
                
                # Absolute capacity C (mAh)
                cap_discharge_abs = q_discharge_abs / 3.6
                cap_charge_abs = q_charge_abs / 3.6
                
                # Selected mass basis in grams
                m_basis_g = m_basis / 1000.0
                
                # Potential Window Calculation: ΔV = |V_end - V_start| in Volts
                delta_V_si = np.abs(v_end_si - v_start_si)
                delta_V_si_safe = max(delta_V_si, 1e-6)
                
                # Capacity Unit conversion function
                def convert_capacity(cap_abs_mah, q_abs_c, unit, mass_g):
                    if unit == "mAh/g":
                        return cap_abs_mah / mass_g
                    elif unit == "Ah/g":
                        return (cap_abs_mah / 1000.0) / mass_g
                    elif unit == "C/g":
                        return q_abs_c / mass_g
                    elif unit == "mAh":
                        return cap_abs_mah
                    return cap_abs_mah
                
                # Capacitance Unit conversion function
                # Base Specific Capacitance (F/g) = Specific Charge (C/g) / ΔV
                def convert_capacitance(q_abs_c, delta_v, unit, mass_g, area_val=1.0):
                    q_spec_cg = q_abs_c / mass_g  # specific charge (C/g)
                    cap_sp_fg = q_spec_cg / delta_v  # specific capacitance (F/g)
                    
                    if unit == "F/g":
                        return cap_sp_fg
                    elif unit == "mF/g":
                        return cap_sp_fg * 1000.0
                    elif unit == "F/cm²":
                        return q_abs_c / (area_val * delta_v)
                    return cap_sp_fg
                
                # Calculate Capacity values
                val_discharge_cap = convert_capacity(cap_discharge_abs, q_discharge_abs, capacity_unit, m_basis_g)
                val_charge_cap = convert_capacity(cap_charge_abs, q_charge_abs, capacity_unit, m_basis_g)
                
                # Calculate Capacitance values based on DISCHARGE area
                area_cm2 = electrode_area if capacitance_unit == "F/cm²" else 1.0
                val_discharge_capacitance = convert_capacitance(q_discharge_abs, delta_V_si_safe, capacitance_unit, m_basis_g, area_cm2)
                val_charge_capacitance = convert_capacitance(q_charge_abs, delta_V_si_safe, capacitance_unit, m_basis_g, area_cm2)
                
                # Coulombic Efficiency calculation (%)
                coulombic_eff = (val_discharge_cap / val_charge_cap * 100.0) if val_charge_cap > 0.0 else 0.0
                
                # Format subtext descriptions
                mass_details = f"Cathode: {m_cathode:.2f}mg | Anode: {m_anode:.2f}mg | Basis: {m_basis_toggle}"
                
                if is_normalized:
                    correction_sub = f"Software mass correction applied (from {m_original}mg to basis)"
                else:
                    correction_sub = "Raw current integrated over basis mass"
                
                # Render Metrics cards
                st.subheader("📊 Electrochemical Capacity & Capacitance Dashboard")
                
                m_col1, m_col2, m_col3 = st.columns(3)
                with m_col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Discharge Metrics (Cathodic)</div>
                        <div class="metric-value">{val_discharge_cap:.3f} <span style="font-size: 1.1rem;">{capacity_unit}</span></div>
                        <div class="metric-value-sub">{val_discharge_capacitance:.3f} <span style="font-size: 1rem;">{capacitance_unit}</span></div>
                        <div class="metric-sub">{mass_details}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m_col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Charge Metrics (Anodic)</div>
                        <div class="metric-value">{val_charge_cap:.3f} <span style="font-size: 1.1rem;">{capacity_unit}</span></div>
                        <div class="metric-value-sub" style="color: #f59e0b;">{val_charge_capacitance:.3f} <span style="font-size: 1rem;">{capacitance_unit}</span></div>
                        <div class="metric-sub">{correction_sub}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m_col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Coulombic Efficiency</div>
                        <div class="metric-value" style="color: #6366f1;">{coulombic_eff:.2f}%</div>
                        <div class="metric-value-sub" style="color: #a5b4fc; font-size: 1.25rem;">ΔV: {delta_V_si:.3f} V</div>
                        <div class="metric-sub">Scan Rate: {scan_rate_val} {scan_rate_unit} ({scan_rate_si:.3e} V/s)</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Matplotlib Plot in User units
                col_plot, col_data = st.columns([2, 1])
                
                # Map curves back to display units
                voltage_display = voltage_bins_si / factor_V
                p_voltages_display = V_si / factor_V
                
                if is_normalized:
                    div_mass = m_original / 1000.0
                    upper_curve_display = (upper_curve_raw_A / div_mass) / factor_I
                    lower_curve_display = (lower_curve_raw_A / div_mass) / factor_I
                    charge_branch_display = (charge_branch_si / div_mass) / factor_I
                    discharge_branch_display = (discharge_branch_si / div_mass) / factor_I
                    p_currents_display = (I_raw_A / div_mass) / factor_I
                else:
                    upper_curve_display = upper_curve_raw_A / factor_I
                    lower_curve_display = lower_curve_raw_A / factor_I
                    charge_branch_display = charge_branch_si / factor_I
                    discharge_branch_display = discharge_branch_si / factor_I
                    p_currents_display = I_raw_A / factor_I
                
                with col_plot:
                    fig, ax = plt.subplots(figsize=(8, 5))
                    fig.patch.set_facecolor('#0e1117')
                    ax.set_facecolor('#1e293b')
                    
                    # Plot raw pixels
                    ax.scatter(p_voltages_display, p_currents_display, color='#64748b', alpha=0.3, s=4, label="Raw Pixels")
                    
                    # Plot binned curves
                    ax.plot(voltage_display, upper_curve_display, color='#ef4444', linewidth=2.5, label="Upper Curve")
                    ax.plot(voltage_display, lower_curve_display, color='#38bdf8', linewidth=2.5, label="Lower Curve")
                    
                    # Shading independent integration areas
                    ax.fill_between(voltage_display, discharge_branch_display, 0, where=(discharge_branch_display < 0), color='#38bdf8', alpha=0.15, label="Discharge Area (I < 0)")
                    ax.fill_between(voltage_display, charge_branch_display, 0, where=(charge_branch_display > 0), color='#ef4444', alpha=0.1, label="Charge Area (I > 0)")
                    
                    ax.set_xlabel(f"Potential ({potential_unit})", color='white', fontsize=12)
                    ax.set_ylabel(f"Current ({current_unit})", color='white', fontsize=12)
                    ax.set_title("Reconstructed CV Curves and Integration Areas", color='white', fontsize=14, pad=15)
                    
                    ax.grid(color='#334155', linestyle='--', linewidth=0.5)
                    ax.tick_params(colors='white')
                    ax.spines['bottom'].set_color('#334155')
                    ax.spines['top'].set_color('#334155')
                    ax.spines['left'].set_color('#334155')
                    ax.spines['right'].set_color('#334155')
                    
                    legend = ax.legend(facecolor='#1e293b', edgecolor='#334155')
                    plt.setp(legend.get_texts(), color='white')
                    
                    st.pyplot(fig)
                
                with col_data:
                    st.subheader("📥 Export Extracted Data")
                    st.markdown("Download the reconstructed curves mapped into your chosen units.")
                    
                    export_df = pd.DataFrame({
                        f"Potential_{potential_unit}": voltage_display,
                        f"Anodic_Current_{current_unit}": upper_curve_display,
                        f"Cathodic_Current_{current_unit}": lower_curve_display
                    })
                    
                    st.dataframe(export_df.round(5), use_container_width=True, height=250)
                    
                    csv_io = io.StringIO()
                    export_df.to_csv(csv_io, index=False)
                    st.download_button(
                        label="Download Curve Data as CSV",
                        data=csv_io.getvalue(),
                        file_name="extracted_cv_units_scaled.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.error("🚨 Failed to reconstruct continuous curve. Please adjust HSV threshold settings to capture more points of the line.")
