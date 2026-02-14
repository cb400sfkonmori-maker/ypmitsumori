
# Steel Pole Material Estimation App
(鋼管柱・自動拾い出しシステム)

## Overview
This application automates the material estimation from steel pole assembly drawings using AI (Gemini 1.5 Pro).
It extracts component dimensions, calculates weights with specific industry logic (overlap correction, base plate rules), and exports to Excel.

## Setup
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   (Streamlit, Pandas, OpenPyXL, Google-GenerativeAI, Pillow)

2. **Run the App**:
   ```bash
   streamlit run app.py
   ```

3. **API Key**:
   You need a Google Gemini API Key. (Get one at https://aistudio.google.com/)
   Enter it in the sidebar when the app starts.

## Features
- **AI Vision Analysis**: Automatically identifies Pipes and Plates from drawings.
- **Auto-Correction**:
  - Adds 400mm overlap for pipe connections.
  - Highlights Base Plate thickness verification.
- **Logic**:
  - Pipe Weight: `(D-t)*t*0.02466`
  - Plate Weight: `Area*t*7.85`
- **Excel Export**: Download the estimation sheet directly.

## Usage
1. Upload a drawing (Image).
2. Click "Analyze Drawing with AI".
3. Check the extracted data in the table.
   - **Important**: Verify "Base Plate" thickness.
   - **Important**: Check "Overlap Count" for split poles.
4. Download the Excel report.
