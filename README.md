# Zn//MnO₂ Cyclic Voltammetry (CV) Capacity & Capacitance Analyzer

A production-ready, mobile-friendly Streamlit web application designed to digitize Cyclic Voltammetry (CV) graph photos and screen captures, isolate the curve using OpenCV-based color segmentation, and compute specific charge capacity, specific capacitance, and Coulombic efficiency.

---

## ⚡ Key Features

1. **Camera & File Inputs**: Supports direct file uploads (PNG, JPG, JPEG) or live photos taken with a phone camera (`st.camera_input`).
2. **Interactive HSV Color Masking**: Easily isolates target curve colors (e.g. blue) from background gridlines, glare, and black axes text using sliders or pre-tuned presets.
3. **Axis Calibration Box**: Allows users to crop and align a calibration grid box with the physical axes, translating image pixel coordinates directly to potential ($V$) and current ($I$).
4. **Independent Integration Engine**: Clips and integrates the anodic (charge, $I > 0$) and cathodic (discharge, $I < 0$) loops separately using the trapezoidal rule to calculate capacity.
5. **Zn//MnO₂ Specific Mass Normalization**:
   - **Cathode Mass Only**: Normalizes capacity and capacitance values using the active MnO₂ cathode mass alone (standard research practice when Zn is in excess).
   - **Total Mass (Cathode + Anode)**: Normalizes using both cathode and anode active masses to determine realistic cell-level specific performance.
6. **Flexible Unit Conversions**: Supports dynamic unit settings for Potential ($V$, $mV$), Current ($A/g$, $mA/g$, $A$, $mA$, $uA$), Scan Rate ($mV/s$, $V/s$, $uV/s$), Capacity ($mAh/g$, $Ah/g$, $C/g$, $mAh$), and Capacitance ($F/g$, $mF/g$, $F/cm²$).

---

## ⚖️ Zn//MnO₂ Mass Normalization Rules

In zinc-ion battery (ZIB) systems, specific charge values depend on how active masses are accounted for:
* **Cathode-Specific Normalization (MnO₂)**:
  $$C_{\text{specific}} = \frac{C_{\text{absolute}}}{M_{\text{cathode}}}$$
  MnO₂ is usually the limiting active mass in half-cell studies, while the zinc anode is supplied in excess.
* **Full-Cell / Total Mass Normalization (Zn + MnO₂)**:
  $$C_{\text{specific}} = \frac{C_{\text{absolute}}}{M_{\text{cathode}} + M_{\text{anode}}}$$
  Provides a realistic metric for commercial-grade pouch or coin cell practical energy densities where anode thickness/mass is balanced.

---

## 🚀 1-Click Deployment to Streamlit Community Cloud

This project is pre-packaged for quick cloud deployment. Follow these instructions to publish your application:

### Step 1: Push Project to GitHub
1. Create a new repository on GitHub (e.g., `zn-mno2-cv-analyzer`).
2. Run the following commands in your local project root directory to push the files:
   ```bash
   git init
   git add app.py requirements.txt README.md assets/
   git commit -m "Initial commit of CV Analyzer"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
   git push -u origin main
   ```

### Step 2: Deploy to Streamlit Cloud
1. Navigate to **[Streamlit Community Cloud](https://share.streamlit.io)** and log in using your GitHub account.
2. Click the **"New app"** button.
3. Select your repository (`zn-mno2-cv-analyzer`), branch (`main`), and set the main file path to:
   ```text
   app.py
   ```
4. Click **"Deploy!"**. Streamlit will configure the virtual environment using `requirements.txt` (installing `opencv-python-headless` automatically to resolve display driver dependencies) and host your web app on a public URL.
