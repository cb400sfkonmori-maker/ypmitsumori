import streamlit as st
import pandas as pd
import logic
import ai_analysis
import visualizer
from io import BytesIO
from PIL import Image
from streamlit_pdf_viewer import pdf_viewer
st.set_page_config(layout="wide", page_title="Steel Pole Estimator (鋼管柱積算)")

st.title("🔩 Steel Pole Material Estimation System")
st.markdown("**(鋼管柱・自動拾い出しシステム)**")
st.caption("Produced by AxelOn Inc.")

# Sidebar for Setup
with st.sidebar:
    st.header("1. Setup (設定)")
    api_key = st.text_input("Enter Gemini API Key (APIキーを入力)", type="password")
    uploaded_file = st.file_uploader("Upload Drawing (図面アップロード)", type=["png", "jpg", "jpeg", "pdf"])
    
    st.divider()
    st.header("Cost Settings (原価設定)")
    # Material Unit Costs
    price_pipe_steel = st.sidebar.number_input("Unit Price: Pipe (鋼管単価 ¥/kg)", value=311, step=10)
    price_plate_steel = st.sidebar.number_input("Unit Price: Plate (板材単価 ¥/kg)", value=396, step=10)
    price_galv_process = st.sidebar.number_input("Galvanizing (メッキ単価 ¥/kg)", value=85, step=5)
    
    # Labor & Efficiency
    # Labor & Efficiency
    labor_rate_weld = st.sidebar.number_input("Labor Rate: Welding (溶接単価 ¥/H)", value=4244, step=100)
    labor_rate_paint = st.sidebar.number_input("Labor Rate: Painting (塗装単価 ¥/H)", value=12530, step=100)
    price_paint_mat = st.sidebar.number_input("Paint Mat. Price (塗料単価 ¥/m²)", value=1700, step=100)
    weld_speed_mm_min = st.sidebar.number_input("Weld Eff. (溶接能率 mm/min)", value=50, step=5)
    paint_eff_m2_h = st.sidebar.number_input("Paint Eff. (塗装能率 m²/H)", value=1.5, step=0.1)
    
    st.divider()
    st.header("Markup Settings (掛率設定)")
    overhead_rate = st.sidebar.slider("Overhead & Profit (%)", 0, 50, 20, 1)
    contingency_rate = st.sidebar.slider("Risk Contingency (%)", 0, 20, 5, 1)

    st.divider()
    st.info("💡 **Tips (ヒント):**\n- 図面が鮮明であることを確認してください。\n- ベースプレートの板厚は必ず目視確認してください。\n- ジョイントの重なり数を確認してください。")

if uploaded_file:
    # ... (Image handling same as before) ...
    # Attempt to open image for preview and analysis
    image = None
    try:
        image = Image.open(uploaded_file)
    except Exception:
        pass # Might be PDF or other format

    # Display Image (Left Column or Top)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("2. Drawing Preview (図面プレビュー)")
        if image:
            st.image(image, use_container_width=True)
        elif uploaded_file.type == "application/pdf":
            st.info(f"📄 PDFファイルがアップロードされました: {uploaded_file.name}")
            # PDF Preview
            binary_data = uploaded_file.getvalue()
            pdf_viewer(input=binary_data, width=700)
        else:
            st.info("プレビューを表示できません (Preview not available). 解析に進んでください。")

    with col2:
        st.subheader("3. Material Extraction (部材抽出)")
        
        # Session State for Data
        if "extracted_data" not in st.session_state:
            st.session_state.extracted_data = []

        if st.button("🚀 Analyze Drawing with AI (AI解析開始)"):
            if not api_key:
                st.warning("APIキーを入力してください (Please enter an API Key first).")
                # TODO: Remove dummy data in production or make optional
                st.info("デモデータを使用します (Using Dummy Data)...")
                data = ai_analysis.get_dummy_data()
                st.session_state.extracted_data = data
            else:
                with st.spinner("解析中... (Analyzing... 10-20秒かかります)"):
                    try:
                        # Use the opened image if available, otherwise pass the file object
                        target_file = image if image else uploaded_file
                        
                        # PDF support enabled
                        data = ai_analysis.analyze_drawing(target_file, api_key)
                        if data:
                            st.session_state.extracted_data = data
                            st.success("解析完了! (Analysis Complete)")
                        else:
                            st.error("データが抽出されませんでした (No data extracted).")
                    except Exception as e:
                        st.error(f"Error: {e}")

        # Data Editor
        if len(st.session_state.extracted_data) > 0:
            # Migration check
            if isinstance(st.session_state.extracted_data[0], dict) and "pattern_name" not in st.session_state.extracted_data[0]:
                 st.session_state.extracted_data = [{"pattern_name": "Default Pattern", "components": st.session_state.extracted_data}]

            patterns = st.session_state.extracted_data
            
            # Create Tabs for each Pattern
            pattern_names = [p.get("pattern_name", f"Pattern {i+1}") for i, p in enumerate(patterns)]
            tabs = st.tabs(pattern_names)
            
            # Store final dataframes for Export
            final_dfs_for_export = {}

            # --- Common Logic / Helpers ---
            def get_float_helper(val):
                try: 
                    if isinstance(val, str):
                        val = val.replace(",", "")
                    return float(val)
                except: return 0.0

            def calculate_row(row):
                 try:
                    d = get_float_helper(row.get("diameter_mm", 0))
                    t = get_float_helper(row.get("thickness_mm", 0))
                    l = get_float_helper(row.get("length_mm", 0))
                    w = get_float_helper(row.get("width_mm", 0))
                    c = get_float_helper(row.get("count", 1))
                    
                    # Handle overlap count safely (ensure it's treated as float then int)
                    overlap_val = row.get("overlap_count", 0)
                    overlap = int(get_float_helper(overlap_val))
                    
                    ctype = str(row.get("type", "")).lower()
                    name = str(row.get("name", "")).lower()
                    is_rib = "rib" in name
                    
                    # Perform Calculations using logic module
                    if "pipe" in ctype or "管" in ctype:
                        # Pipe Weight
                        u_w = logic.calculate_pipe_weight(d, t, l, overlap)
                        row["Unit Weight (kg)"] = u_w
                        
                        # Pipe Surface Area
                        s_area = logic.calculate_surface_area(d, l, w, "pipe", overlap, is_rib=False)
                    else:
                        # Plate Weight
                        u_w = logic.calculate_plate_weight(l, w, t, is_rib=is_rib)
                        row["Unit Weight (kg)"] = u_w
                        
                        # Plate Surface Area
                        s_area = logic.calculate_surface_area(d, l, w, "plate", overlap, is_rib=is_rib)
                    
                    # Totals
                    row["Total Weight (kg)"] = round(u_w * c, 2)
                    row["Surface Area (m²)"] = round(s_area * c, 2)

                 except Exception as e:
                    # In case of calculation error, retain 0 but don't crash
                    row["Unit Weight (kg)"] = 0.0
                    row["Total Weight (kg)"] = 0.0
                    row["Surface Area (m²)"] = 0.0
                 
                 return row

            total_project_weight = 0.0
            total_project_area = 0.0

            for i, tab in enumerate(tabs):
                with tab:
                    pattern = patterns[i]
                    components = pattern.get("components", [])
                    st.caption(f"Analyzing Pattern: {pattern.get('pattern_name')}")

                    # --- Validation Alerts (AI Report) ---
                    alerts = pattern.get("validation_alerts", [])
                    if alerts:
                        with st.container():
                            st.error(f"⚠️ **Validation Required (要確認箇所 detected)**")
                            for alert in alerts:
                                st.markdown(f"- {alert}")
                    
                    if not components:
                        st.warning("No components in this pattern.")
                        continue

                    df = pd.DataFrame(components)

                    # Ensure columns exist
                    required_cols = ["type", "name", "diameter_mm", "thickness_mm", "length_mm", "width_mm", "count", "notes"]
                    for col in required_cols:
                        if col not in df.columns:
                            df[col] = "" 

                    # Add "Overlap Count"
                    if "overlap_count" not in df.columns:
                            df["overlap_count"] = df.apply(lambda row: 1 if "Overlap" in str(row.get("notes", "")) else 0, axis=1)

                    # --- Rib Logic Context ---
                    base_w = 0.0
                    pole_max_d = 0.0
                    for _, row in df.iterrows():
                        name = str(row.get("name", "")).lower()
                        ctype = str(row.get("type", "")).lower()
                        if "base" in name and "plate" in ctype: 
                                w = get_float_helper(row.get("width_mm", 0))
                                l = get_float_helper(row.get("length_mm", 0))
                                base_w = max(w, l)
                        if "pipe" in ctype:
                                d = get_float_helper(row.get("diameter_mm", 0))
                                if d > pole_max_d: pole_max_d = d
                    
                    # --- Data Validation & Sorting Logic ---
                    def validate_and_update(row):
                        # 1. Rib Logic
                        name = str(row.get("name", "")).lower()
                        notes = str(row.get("notes", "")) if row.get("notes") else ""
                        needs_check = False
                        
                        if "rib" in name:
                            c = get_float_helper(row.get("count", 0))
                            if c == 0:
                                row["count"] = 4
                                notes += " [Default: 4]"
                            w = get_float_helper(row.get("width_mm", 0))
                            if w == 0 and base_w > 0 and pole_max_d > 0:
                                calc_w = (base_w - pole_max_d) / 2
                                if calc_w > 0:
                                    row["width_mm"] = round(calc_w, 1)
                                    notes += f" [Calc. Width: {calc_w:.1f}]"
                        
                        # 2. Unclear Data Check
                        # Check critical dimensions for 'CHECK' string or 0 value (except reasonable 0s like width for pipe)
                        check_cols = ["diameter_mm", "thickness_mm", "length_mm"]
                        # For Plate, Width is critical. For Pipe, Width is usually 0.
                        ctype = str(row.get("type", "")).lower()
                        if "plate" in ctype:
                            check_cols.append("width_mm")
                            
                        dims_missing = []
                        for col in check_cols:
                            val = row.get(col)
                            # String check
                            if isinstance(val, str) and "CHECK" in val.upper():
                                dims_missing.append(col)
                                needs_check = True
                            # Value check (if numeric 0)
                            else:
                                f_val = get_float_helper(val)
                                if f_val <= 0:
                                    dims_missing.append(col)
                                    needs_check = True

                        if needs_check:
                            row["_priority"] = 1 # Top priority
                            if "⚠️" not in notes:
                                notes = f"⚠️ CHECK: {', '.join(dims_missing)} " + notes
                        else:
                            row["_priority"] = 2
                            
                        row["notes"] = notes.strip()
                        return row

                    df = df.apply(validate_and_update, axis=1)
                    
                    # Sort by priority (Problematic rows first)
                    if "_priority" in df.columns:
                        df = df.sort_values(by="_priority")
                        # Clean up temp column
                        # df = df.drop(columns=["_priority"]) # Keep it hidden or drop? Drop is cleaner.
                        # Actually we need to drop it before display, but keeping it in session state might complicate saving. 
                        # Let's drop it now.

                    # Reorder
                    field_order = ["type", "name", "diameter_mm", "thickness_mm", "length_mm", "width_mm", "count", "overlap_count", "notes"]
                    df = df[[c for c in field_order if c in df.columns]]

                    # Validation Warnings (Manual Logic - kept as backup)
                    potential_issues = []
                    base_plate_found = False
                    for idx, row in df.iterrows():
                        name = str(row.get("name", "")).lower()
                        t_val = row.get("thickness_mm", 0)
                        try:
                            if t_val and "CHECK" not in str(t_val):
                                thickness = float(str(t_val).replace(",", ""))
                                if "base" in name and "plate" in name:
                                    base_plate_found = True
                                    if thickness < 12 and thickness > 0: 
                                            potential_issues.append(f"⚠️ Row {idx+1}: Thickness {thickness}mm seems thin for Base Plate.")
                        except: pass
                    
                    if not base_plate_found and len(df) > 0:
                        potential_issues.append("⚠️ No component named 'Base Plate' found.")
                    
                    if potential_issues:
                        with st.expander("Additional Logic Warnings", expanded=True):
                            for issue in potential_issues:
                                st.markdown(issue)

                    # Pre-calculation conversion for stability
                    numeric_cols = ["diameter_mm", "thickness_mm", "length_mm", "width_mm", "count", "overlap_count"]
                    for col in numeric_cols:
                        if col in df.columns:
                            # Convert to consistent numeric type, coerce errors to NaN then 0
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                    # Initial Calculation mainly for Total/Area columns
                    df_calculated = df.apply(calculate_row, axis=1)
                    
                    # Editor
                    edited_df = st.data_editor(
                        df_calculated,
                        column_config={
                            "type": st.column_config.TextColumn("部材タイプ"),
                            "name": st.column_config.TextColumn("部材名"),
                            "diameter_mm": st.column_config.NumberColumn("外径 (Dia)", help="mm", format="%.1f"),
                            "thickness_mm": st.column_config.NumberColumn("板厚 (Thk)", help="mm", format="%.1f"),
                            "length_mm": st.column_config.NumberColumn("長さ (Len)", help="mm", format="%.0f"),
                            "width_mm": st.column_config.NumberColumn("幅 (Wid)", help="mm", format="%.1f"),
                            "count": st.column_config.NumberColumn("数量 (Qty)", format="%.0f"),
                            "overlap_count": st.column_config.NumberColumn("継手間隔", format="%.0f"),
                            "notes": st.column_config.TextColumn("備考 (Notes)"),
                            "Unit Weight (kg)": st.column_config.NumberColumn("単重 (Unit kg)", disabled=True, format="%.2f"),
                            "Total Weight (kg)": st.column_config.NumberColumn("重量 (Total kg)", disabled=True, format="%.2f"),
                            "Surface Area (m²)": st.column_config.NumberColumn("塗装面積 (Area)", disabled=True, format="%.2f"),
                        },
                        use_container_width=True,
                        key=f"editor_{i}",
                        num_rows="dynamic"
                    )

                    # Reactive Recalc
                    final_df = edited_df.apply(calculate_row, axis=1)
                    
                    # Update Session State
                    st.session_state.extracted_data[i]["components"] = final_df.to_dict('records')
                    final_dfs_for_export[pattern.get("pattern_name", f"Pattern {i}")] = final_df
                    
                    # Metrics
                    p_weight = final_df["Total Weight (kg)"].sum()
                    p_area = final_df["Surface Area (m²)"].sum()
                    
                    # --- Cost Calculations ---
                    # 1. Material Cost (Row Level)
                    def is_pipe(row):
                        t = str(row.get("type", "")).lower()
                        return "pipe" in t or "管" in t
                        
                    def calc_material_cost(row):
                        w = row.get("Total Weight (kg)", 0)
                        price = price_pipe_steel if is_pipe(row) else price_plate_steel
                        return w * price

                    final_df["Material Unit Price (¥/kg)"] = final_df.apply(lambda r: price_pipe_steel if is_pipe(r) else price_plate_steel, axis=1)
                    final_df["Material Cost (¥)"] = final_df.apply(calc_material_cost, axis=1)
                    
                    # Re-save to export dict with new columns
                    final_dfs_for_export[pattern.get("pattern_name", f"Pattern {i}")] = final_df

                    # Aggregate Material Cost
                    cost_mat = final_df["Material Cost (¥)"].sum()
                    
                    # 2. Process Cost (Galvanizing)
                    cost_galv = p_weight * price_galv_process
                    
                    # 3. Labor Cost (Estimation) using Weld Speed heuristic
                    total_weld_len_mm = 0.0
                    for _, r in final_df.iterrows():
                        try:
                            d_val = float(str(r.get("diameter_mm", 0)))
                            l_val = float(str(r.get("length_mm", 0)))
                            w_val = float(str(r.get("width_mm", 0)))
                            c_val = float(str(r.get("count", 1)))
                            
                            if d_val > 0: 
                                total_weld_len_mm += (d_val * 3.14159) * 2 * c_val
                            elif l_val > 0 and w_val > 0:
                                total_weld_len_mm += (l_val + w_val) * 2 * c_val
                        except: pass
                        
                    weld_time_h = (total_weld_len_mm / (weld_speed_mm_min * 60)) if weld_speed_mm_min > 0 else 0
                    paint_time_h = (p_area / paint_eff_m2_h) if paint_eff_m2_h > 0 else 0
                    
                    cost_weld = weld_time_h * labor_rate_weld
                    cost_paint = paint_time_h * labor_rate_paint
                    cost_labor = cost_weld + cost_paint
                    
                    cost_paint_mat = p_area * price_paint_mat
                    
                    # 1. Base Cost (製造原価)
                    cost_base = cost_mat + cost_galv + cost_labor + cost_paint_mat
                    
                    # 2. Add-ons
                    overhead_amount = cost_base * (overhead_rate / 100)
                    contingency_amount = cost_base * (contingency_rate / 100)
                    
                    # 3. Grand Total (見積金額)
                    price_est_total = cost_base + overhead_amount + contingency_amount
                    
                    # Global Totals
                    total_project_weight += p_weight
                    total_project_area += p_area
                    
                    # Display Metrics
                    st.divider()
                    st.subheader("💰 Quotation Estimation (見積算出)")
                    
                    # Row 1: Key Figures
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Weight", f"{p_weight:,.1f} kg")
                    m2.metric("Base Cost (原価)", f"¥{cost_base:,.0f}")
                    m3.metric("Quotation Price (見積金額)", f"¥{price_est_total:,.0f}", delta=f"+{overhead_rate+contingency_rate}% Markup")
                    
                    st.caption(f"Breakdown: Base ¥{cost_base:,.0f} + OH ¥{overhead_amount:,.0f} ({overhead_rate}%) + Risk ¥{contingency_amount:,.0f} ({contingency_rate}%)")

                    with st.expander("Show Base Cost Details (原価詳細)", expanded=False):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Material", f"¥{cost_mat:,.0f}")
                        c2.metric("Galvanizing", f"¥{cost_galv:,.0f}")
                        c3.metric("Paint Mat.", f"¥{cost_paint_mat:,.0f}")
                        c4.metric("Labor", f"¥{cost_labor:,.0f}")
                        
                        summary_text = f"**{pattern.get('pattern_name')} Base Cost Breakdown:**\n"
                        summary_text += f"- Material: ¥{cost_mat:,.0f}\n"
                        summary_text += f"- Galvanizing: ¥{cost_galv:,.0f} (@¥{price_galv_process}/kg)\n"
                        summary_text += f"- Paint Material: ¥{cost_paint_mat:,.0f} (@¥{price_paint_mat}/m²)\n"
                        summary_text += f"- Labor: ¥{cost_labor:,.0f} (Weld @¥{labor_rate_weld}/h, Paint @¥{labor_rate_paint}/h)\n"
                        summary_text += f"  - Weld: {total_weld_len_mm/1000:,.1f}m -> {weld_time_h:.1f}H -> ¥{cost_weld:,.0f}\n"
                        summary_text += f"  - Paint: {p_area:.1f}m² -> {paint_time_h:.1f}H -> ¥{cost_paint:,.0f}"
                        st.markdown(summary_text)

                    # --- Report Generation (Per Pattern) ---
                    def generate_report_excel(p_name, df, settings):
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            workbook = writer.book
                            worksheet = workbook.add_worksheet("Estimation Report")
                            
                            # Formats
                            fmt_title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'border': 1, 'bg_color': '#D9E1F2'})
                            fmt_header = workbook.add_format({'bold': True, 'font_size': 11, 'align': 'center', 'border': 1, 'bg_color': '#D9E1F2'})
                            fmt_label = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#F2F2F2'})
                            fmt_input = workbook.add_format({'border': 1, 'bg_color': '#FFF2CC'}) # Input cells yellow
                            fmt_calc = workbook.add_format({'border': 1, 'bg_color': '#E2EFDA'}) # Calc cells green
                            fmt_num = workbook.add_format({'border': 1, 'num_format': '#,##0.0'})
                            fmt_money = workbook.add_format({'border': 1, 'num_format': '¥#,##0'})
                            
                            fmt_money_bold = workbook.add_format({'bold': True, 'border': 1, 'num_format': '¥#,##0', 'font_size': 12})
                            
                            # Settings Unpack
                            galv_price = settings['galv_price']
                            rate_weld = settings['rate_weld']
                            rate_paint = settings['rate_paint']
                            price_paint_mat = settings['price_paint_mat']
                            time_weld = settings['time_weld']
                            time_paint = settings['time_paint']
                            rate_oh = settings['rate_oh']
                            rate_risk = settings['rate_risk']
                            
                            # Layout Definition
                            # Row 0: Title
                            worksheet.merge_range('A1:J1', f"Steel Pole Estimation Report: {p_name}", fmt_title)
                            
                            # Row 2: Metadata
                            worksheet.write('A2', "Date:", fmt_label)
                            from datetime import datetime
                            worksheet.write('B2', datetime.now().strftime("%Y-%m-%d"), fmt_input)
                            worksheet.write('D2', "PRODUCER:", fmt_label)
                            worksheet.write('E2', "AxelOn Inc.", fmt_input)

                            # --- Cost Summary & Parameters Area ---
                            # Define Rows for sections
                            row_summary = 4
                            row_params = 16
                            row_data_header = 24
                            
                            # A. Calculation Parameters ( 積算条件 / 編集エリア )
                            worksheet.merge_range(row_params, 0, row_params, 3, "▼ Calculation Parameters (積算条件・編集可)", fmt_header)
                            # Weld Hours
                            worksheet.write(row_params+1, 0, "Weld Hours (h)", fmt_label)
                            worksheet.write_number(row_params+1, 1, time_weld, fmt_input) # B18
                            cell_weld_h = f"B{row_params+2}"
                            
                            # Paint Hours
                            worksheet.write(row_params+2, 0, "Paint Hours (h)", fmt_label)
                            worksheet.write_number(row_params+2, 1, time_paint, fmt_input) # B19
                            cell_paint_h = f"B{row_params+3}"
                            
                            # OH Rate
                            worksheet.write(row_params+3, 0, "Overhead Rate (%)", fmt_label)
                            worksheet.write_number(row_params+3, 1, rate_oh, fmt_input) # B20
                            cell_rate_oh = f"B{row_params+4}"
                            
                            # Risk Rate
                            worksheet.write(row_params+4, 0, "Risk Rate (%)", fmt_label)
                            worksheet.write_number(row_params+4, 1, rate_risk, fmt_input) # B21
                            cell_rate_risk = f"B{row_params+5}"

                            # Rates (Right Side)
                            worksheet.write(row_params+1, 2, "Weld Rate (¥/h)", fmt_label)
                            worksheet.write_number(row_params+1, 3, rate_weld, fmt_input) 
                            cell_rate_weld = f"D{row_params+2}"
                            
                            worksheet.write(row_params+2, 2, "Paint Rate (¥/h)", fmt_label)
                            worksheet.write_number(row_params+2, 3, rate_paint, fmt_input) 
                            cell_rate_paint = f"D{row_params+3}"
                            
                            worksheet.write(row_params+3, 2, "Paint Mat. (¥/m2)", fmt_label)
                            worksheet.write_number(row_params+3, 3, price_paint_mat, fmt_input) 
                            cell_price_paint_mat = f"D{row_params+4}"

                            worksheet.write(row_params+4, 2, "Galv Unit Price (¥/kg)", fmt_label)
                            worksheet.write_number(row_params+4, 3, galv_price, fmt_input) 
                            cell_price_galv = f"D{row_params+5}"

                            # B. Cost Summary ( 原価サマリー / 式 )
                            worksheet.merge_range(row_summary, 0, row_summary, 2, "▼ Cost Summary (原価サマリー)", fmt_header)
                            
                            # Define Ranges for Data (To be determined after writing data)
                            range_data_start = row_data_header + 2
                            # placeholders for formula
                            
                            # 1. Total Weight
                            worksheet.write(row_summary+1, 0, "Total Weight (kg)", fmt_label)
                            # Formula: SUM(H_data)
                            
                            # 2. Material Cost
                            worksheet.write(row_summary+2, 0, "Material Cost (¥)", fmt_label)
                            # Formula: SUM(J_data)
                            
                            # 3. Galvanizing Cost
                            worksheet.write(row_summary+3, 0, "Galvanizing Cost (¥)", fmt_label)
                            # Formula: TotalWeight * GalvPrice
                            
                            # 4. Paint Material Cost
                            worksheet.write(row_summary+4, 0, "Paint Material Cost (¥)", fmt_label)
                            # Formula will be set later using cell_price_paint_mat
                            
                            # 5. Welding Cost
                            worksheet.write(row_summary+5, 0, "Welding Labor Cost (¥)", fmt_label)
                            worksheet.write_formula(row_summary+5, 1, f"={cell_weld_h}*{cell_rate_weld}", fmt_money)
                            
                            # 6. Painting Cost
                            worksheet.write(row_summary+6, 0, "Painting Labor Cost (¥)", fmt_label)
                            worksheet.write_formula(row_summary+6, 1, f"={cell_paint_h}*{cell_rate_paint}", fmt_money)
                            
                            # 7. TOTAL BASE COST
                            worksheet.write(row_summary+7, 0, "TOTAL BASE COST (製造原価)", fmt_label)
                            # Formula: Mat + Galv + PaintMat + Weld + PaintLabor
                            
                            # 8. Overhead
                            worksheet.write(row_summary+8, 0, "Overhead & Profit (¥)", fmt_label)
                            # Formula: Base * OH%
                            
                            # 9. Contingency
                            worksheet.write(row_summary+9, 0, "Risk Contingency (¥)", fmt_label)
                            # Formula: Base * Risk%
                            
                            # 10. QUOTATION PRICE
                            worksheet.write(row_summary+10, 0, "QUOTATION PRICE (御見積金額)", fmt_header)
                            # Formula: Base + OH + Risk
                            
                            
                            # --- Component Data ---
                            headers = ["Type", "Name", "Dia (mm)", "Thk (mm)", "Len (mm)", "Wid (mm)", "Qty", "Weight (kg)", "Unit Price", "Cost (¥)", "Area (m²)"]
                            for i, h in enumerate(headers):
                                worksheet.write(row_data_header, i, h, fmt_header)
                            
                            import math
                            def safe_num(v):
                                try:
                                    f = float(v)
                                    if math.isnan(f) or math.isinf(f): return 0.0
                                    return f
                                except:
                                    return 0.0

                            current_row = row_data_header + 1
                            for _, r in df.iterrows():
                                # Inputs & Statics
                                worksheet.write(current_row, 0, r.get("type",""), fmt_input)
                                worksheet.write(current_row, 1, r.get("name",""), fmt_input)
                                
                                # Safe Extract & Write
                                d_v = safe_num(r.get("diameter_mm"))
                                t_v = safe_num(r.get("thickness_mm"))
                                l_v = safe_num(r.get("length_mm"))
                                w_v = safe_num(r.get("width_mm"))
                                q_v = safe_num(r.get("count"))
                                mat_price = safe_num(r.get("Material Unit Price (¥/kg)"))

                                worksheet.write_number(current_row, 2, d_v, fmt_input) # C
                                worksheet.write_number(current_row, 3, t_v, fmt_input) # D
                                worksheet.write_number(current_row, 4, l_v, fmt_input) # E
                                worksheet.write_number(current_row, 5, w_v, fmt_input) # F
                                worksheet.write_number(current_row, 6, q_v, fmt_input) # G
                                worksheet.write_number(current_row, 8, mat_price, fmt_input) # I
                                
                                xl_row = current_row + 1
                                # Weight Formula (H)
                                is_pipe = "pipe" in str(r.get("type","")).lower() or "管" in str(r.get("type","")).lower()
                                if is_pipe:
                                    formula_weight = f"=(C{xl_row}-D{xl_row})*D{xl_row}*0.02466*E{xl_row}*G{xl_row}/1000"
                                else:
                                    formula_weight = f"=D{xl_row}*E{xl_row}*F{xl_row}*7.85*G{xl_row}/1000000"
                                worksheet.write_formula(current_row, 7, formula_weight, fmt_calc)
                                
                                # Cost Formula (J)
                                worksheet.write_formula(current_row, 9, f"=H{xl_row}*I{xl_row}", fmt_money)
                                
                                # Helpers
                                pi_v = 3.1416
                                
                                # Logic Check
                                if is_pipe:
                                   # Pipe Area: pi * D * L / 10^6 * Qty
                                   formula_area = f"=3.1416*C{xl_row}*E{xl_row}/1000000*G{xl_row}"
                                   val_area = pi_v * d_v * l_v / 1000000 * q_v
                                   
                                   formula_weld = f"=3.1416*C{xl_row}*2*G{xl_row}" 
                                else:
                                   # Plate Area: 2*(LW+LT+WT)/10^6 * Qty
                                   formula_area = f"=2*(E{xl_row}*F{xl_row}+E{xl_row}*D{xl_row}+F{xl_row}*D{xl_row})/1000000*G{xl_row}"
                                   val_area = 2 * (l_v*w_v + l_v*t_v + w_v*t_v) / 1000000 * q_v
                                   
                                   formula_weld = f"=(E{xl_row}+F{xl_row})*2*G{xl_row}"

                                # Write Area to K (Visible), Weld to L (Hidden)
                                worksheet.write_formula(current_row, 10, formula_area, fmt_calc, val_area)
                                worksheet.write_formula(current_row, 11, formula_weld)
                                
                                current_row += 1
                                
                            last_data_row = current_row
                            
                            # Update Summary Formulas requiring Data Range
                            rng_weight = f"H{row_data_header+2}:H{last_data_row}"
                            rng_cost = f"J{row_data_header+2}:J{last_data_row}"
                            rng_area = f"K{row_data_header+2}:K{last_data_row}"
                            
                            # Total Weight
                            worksheet.write_formula(row_summary+1, 1, f"=SUM({rng_weight})", fmt_num)
                            cell_total_weight = f"B{row_summary+2}"
                            
                            # Material Cost
                            worksheet.write_formula(row_summary+2, 1, f"=SUM({rng_cost})", fmt_money)
                            cell_mat_cost = f"B{row_summary+3}"
                            
                            # Galv Cost Formula: Total Weight * Unit Price
                            worksheet.write_formula(row_summary+3, 1, f"={cell_total_weight}*{cell_price_galv}", fmt_money)
                            cell_galv_cost = f"B{row_summary+4}"
                            
                            # 4. Total Area (New)
                            worksheet.write(row_summary+4, 0, "Total Area (m²)", fmt_label)
                            worksheet.write_formula(row_summary+4, 1, f"=SUM({rng_area})", fmt_num)
                            cell_total_area = f"B{row_summary+5}"

                            # 5. Paint Material Cost
                            worksheet.write(row_summary+5, 0, "Paint Material Cost (¥)", fmt_label)
                            worksheet.write_formula(row_summary+5, 1, f"={cell_total_area}*{cell_price_paint_mat}", fmt_money)
                            cell_paint_mat_cost = f"B{row_summary+6}"
                            
                            # 6. Welding Cost
                            worksheet.write(row_summary+6, 0, "Welding Labor Cost (¥)", fmt_label)
                            worksheet.write_formula(row_summary+6, 1, f"={cell_weld_h}*{cell_rate_weld}", fmt_money)
                            cell_weld_cost = f"B{row_summary+7}"
                            
                            # 7. Painting Cost
                            worksheet.write(row_summary+7, 0, "Painting Labor Cost (¥)", fmt_label)
                            worksheet.write_formula(row_summary+7, 1, f"={cell_paint_h}*{cell_rate_paint}", fmt_money)
                            cell_paint_cost = f"B{row_summary+8}"
                            
                            # 8. Total Base Cost
                            worksheet.write(row_summary+8, 0, "TOTAL BASE COST (製造原価)", fmt_label)
                            worksheet.write_formula(row_summary+8, 1, f"={cell_mat_cost}+{cell_galv_cost}+{cell_paint_mat_cost}+{cell_weld_cost}+{cell_paint_cost}", fmt_money)
                            cell_base_cost = f"B{row_summary+9}"

                            # 9. Overhead
                            worksheet.write(row_summary+9, 0, "Overhead & Profit (¥)", fmt_label)
                            worksheet.write_formula(row_summary+9, 1, f"={cell_base_cost}*({cell_rate_oh}/100)", fmt_money)
                            cell_oh_amt = f"B{row_summary+10}"

                            # 10. Risk
                            worksheet.write(row_summary+10, 0, "Risk Contingency (¥)", fmt_label)
                            worksheet.write_formula(row_summary+10, 1, f"={cell_base_cost}*({cell_rate_risk}/100)", fmt_money)
                            cell_risk_amt = f"B{row_summary+11}"

                            # 11. QUOTATION PRICE
                            worksheet.write(row_summary+11, 0, "QUOTATION PRICE (御見積金額)", fmt_header)
                            worksheet.write_formula(row_summary+11, 1, f"={cell_base_cost}+{cell_oh_amt}+{cell_risk_amt}", fmt_money_bold)

                            # Column Layout
                            worksheet.set_column('A:B', 30)
                            worksheet.set_column('C:G', 10)
                            worksheet.set_column('H:J', 15)
                            worksheet.set_column('K:K', 12)
                            worksheet.set_column('L:L', 2)

                        return output.getvalue()

                    # Settings Dict
                    settings = {
                        'galv_price': price_galv_process,
                        'rate_weld': labor_rate_weld,
                        'rate_paint': labor_rate_paint,
                        'price_paint_mat': price_paint_mat,
                        'time_weld': float(f"{weld_time_h:.1f}"),
                        'time_paint': float(f"{paint_time_h:.1f}"),
                        'rate_oh': overhead_rate,
                        'rate_risk': contingency_rate
                    }
                    excel_data = generate_report_excel(pattern.get('pattern_name'), final_df, settings)
                    
                    st.download_button(
                        label="📄 Generate Official Report (Excel with Formulas)",
                        data=excel_data,
                        file_name=f"Report_{pattern.get('pattern_name')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"btn_report_{i}"
                    )

                    # 3D
                    with st.expander("Show 3D Preview", expanded=True):
                        try:
                            fig_3d = visualizer.generate_3d_preview(final_df, title=f"AxelOn Digital Twin: {pattern.get('pattern_name')}")
                            st.plotly_chart(fig_3d, use_container_width=True, key=f"3d_{i}")
                        except Exception as e:
                            st.error(f"3D Error: {e}")

            # Totals Section
            st.divider()
            st.subheader("🏁 Total Project Summary (全体集計)")
            t1, t2 = st.columns(2)
            t1.metric("Total Project Weight", f"{total_project_weight:,.2f} kg")
            t2.metric("Total Project Area", f"{total_project_area:,.2f} m²")

            # 5. Export
            st.subheader("4. Export (出力)")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for p_name, final_df in final_dfs_for_export.items():
                    # Clean sheet name
                    sheet_name = "".join([c for c in p_name if c.isalnum() or c in (' ','_','-')])[:30]
                    
                    excel_cols = [
                        "type", "name", 
                        "diameter_mm", "thickness_mm", "length_mm", "width_mm", 
                        "count", "overlap_count", 
                        "Unit Weight (kg)", "Total Weight (kg)", 
                        "Material Unit Price (¥/kg)", "Material Cost (¥)",
                        "Surface Area (m²)", "notes"
                    ]
                    valid_cols = [c for c in excel_cols if c in final_df.columns]
                    export_df = final_df[valid_cols].copy()
                    
                    export_df.to_excel(writer, index=False, sheet_name=sheet_name)
                    # (Simplified export without formulas for multi-sheet robustness, or we repeat formula logic)
                    # Users prefer formulas, let's keep it if possible but it complicates the loop.
                    # Start simplistic: Value only for now as formula injection is complex in loop without careful idx tracking.
                    # Or reuse the formula logic? 
                    # Let's add simple formulas if we can.
                    
                    worksheet = writer.sheets[sheet_name]
                    for r_idx, row in enumerate(export_df.itertuples(), start=2):
                        # Simple value fill already done by to_excel. 
                        # Overwrite columns J, K, L with Formulas if we want.
                        # For robustness in this refactor, I will SKIP complex formula injection to ensure stability first.
                        pass

            st.download_button(
                label="📥 Download Excel Report (Multi-Sheet)",
                data=output.getvalue(),
                file_name="steel_pole_estimation.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # 6. Asset Management
            st.divider()
            with st.expander("💾 Save to Digital Archive", expanded=False):
                col_save1, col_save2 = st.columns([2, 1])
                project_name = col_save1.text_input("Project Name (案件名)", value="Project_Alpha_01")
                import json
                from datetime import datetime
                save_data = {
                    "meta": { "project_name": project_name, "created_at": datetime.now().isoformat(), "version": "2.0" },
                    "patterns": st.session_state.extracted_data,
                    "metrics": { "total_weight": total_project_weight, "total_area": total_project_area }
                }
                st.download_button("💾 Save Asset (JSON)", json.dumps(save_data, indent=2, ensure_ascii=False), f"{project_name}_asset.json", "application/json")
else:
    st.info("Please upload a drawing to start.")

