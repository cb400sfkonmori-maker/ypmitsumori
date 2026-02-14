
import plotly.graph_objects as go
import numpy as np
import pandas as pd

def create_cylinder_mesh(diameter, height, z_start, color='lightsteelblue', opacity=0.95):
    """
    Create a cylindrical surface using go.Surface.
    """
    if diameter <= 0 or height <= 0: return None
    
    radius = diameter / 2.0
    # Higher Resolution for smoothness
    theta = np.linspace(0, 2*np.pi, 36)
    z = np.linspace(z_start, z_start + height, 5)
    
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = radius * np.cos(theta_grid)
    y_grid = radius * np.sin(theta_grid)
    
    # Create surface
    # Darker/Metallic colors look better on dark background
    surface = go.Surface(
        x=x_grid, y=y_grid, z=z_grid,
        colorscale=[[0, color], [1, color]],
        showscale=False,
        opacity=opacity,
        # White contours for wireframe effect on dark bg - Enhanced for visibility
        contours_z=dict(show=True, usecolormap=False, highlightcolor="#00ffff", project_z=True, color="white", width=2)
    )
    return surface

def create_box_mesh(length, width, thickness, z_start, color='gray'):
    if length <= 0 or width <= 0 or thickness <= 0: return None
    
    l, w, h = length/2, width/2, thickness
    
    x = [-l, -l, l, l, -l, -l, l, l]
    y = [-w, w, w, -w, -w, w, w, -w]
    z = [z_start, z_start, z_start, z_start, z_start+h, z_start+h, z_start+h, z_start+h]
    
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    
    mesh = go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        color=color,
        opacity=1.0,
        flatshading=True,
        name='Base Plate',
        lighting=dict(ambient=0.6, diffuse=0.9, specular=0.1)
    )
    return mesh

def create_rib_mesh(pipe_radius, rib_w, rib_h, rib_t, z_start, angle_deg, color='darkgray'):
    rad = np.radians(angle_deg)
    cos_a = np.cos(rad)
    sin_a = np.sin(rad)
    t_half = rib_t / 2.0
    
    x_inner = pipe_radius
    x_outer = pipe_radius + rib_w
    
    v_base_inner_l = [x_inner, -t_half, z_start]
    v_base_inner_r = [x_inner, t_half, z_start]
    v_base_outer_l = [x_outer, -t_half, z_start]
    v_base_outer_r = [x_outer, t_half, z_start]
    
    v_top_inner_l = [x_inner, -t_half, z_start + rib_h]
    v_top_inner_r = [x_inner, t_half, z_start + rib_h]
    
    verts = np.array([
        v_base_inner_l, v_base_inner_r, v_base_outer_l, v_base_outer_r,
        v_top_inner_l, v_top_inner_r
    ])
    
    R = np.array([
        [cos_a, -sin_a, 0],
        [sin_a, cos_a, 0],
        [0, 0, 1]
    ])
    
    rotated_verts = verts.dot(R.T)
    x, y, z = rotated_verts[:, 0], rotated_verts[:, 1], rotated_verts[:, 2]
    
    i = [0, 1, 0, 1, 2, 2, 0, 1]
    j = [1, 3, 4, 4, 3, 5, 2, 5]
    k = [2, 2, 1, 5, 5, 4, 4, 3]
    
    return go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=1.0, flatshading=True, name='Rib')

def create_human_mesh(x_offset, y_offset, z_start=0):
    """
    Create a simple 175cm human figure.
    Height: 1750mm. Color: Safety Orange/Human skin.
    Constructed of 3 boxes: Legs, Torso, Head.
    """
    traces = []
    
    # 1. Legs (Block)
    # 900mm tall, 300mm wide, 150mm deep
    lx, ly, lz = 150, 75, 900 # Half dims
    leg_mesh = go.Mesh3d(
        x=[x_offset-lx, x_offset-lx, x_offset+lx, x_offset+lx, x_offset-lx, x_offset-lx, x_offset+lx, x_offset+lx],
        y=[y_offset-ly, y_offset+ly, y_offset+ly, y_offset-ly, y_offset-ly, y_offset+ly, y_offset+ly, y_offset-ly],
        z=[z_start, z_start, z_start, z_start, z_start+900, z_start+900, z_start+900, z_start+900],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='#1E90FF', # Jeans Blue
        flatshading=True, name='Human Legs'
    )
    traces.append(leg_mesh)
    
    # 2. Torso (Block)
    # 600mm tall, 500mm wide (shoulders), 200mm deep
    tx, ty, tz = 200, 100, 600 
    z_torso = z_start + 900
    torso_mesh = go.Mesh3d(
        x=[x_offset-tx, x_offset-tx, x_offset+tx, x_offset+tx, x_offset-tx, x_offset-tx, x_offset+tx, x_offset+tx],
        y=[y_offset-ty, y_offset+ty, y_offset+ty, y_offset-ty, y_offset-ty, y_offset+ty, y_offset+ty, y_offset-ty],
        z=[z_torso, z_torso, z_torso, z_torso, z_torso+600, z_torso+600, z_torso+600, z_torso+600],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='#FF4500', # Orange Shirt
        flatshading=True, name='Human Torso'
    )
    traces.append(torso_mesh)
    
    # 3. Head (Block)
    # 250mm tall
    hx, hy, hz = 100, 100, 250
    z_head = z_torso + 600
    head_mesh = go.Mesh3d(
        x=[x_offset-hx, x_offset-hx, x_offset+hx, x_offset+hx, x_offset-hx, x_offset-hx, x_offset+hx, x_offset+hx],
        y=[y_offset-hy, y_offset+hy, y_offset+hy, y_offset-hy, y_offset-hy, y_offset+hy, y_offset+hy, y_offset-hy],
        z=[z_head, z_head, z_head, z_head, z_head+250, z_head+250, z_head+250, z_head+250],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='#FFD700', # Skin/Gold
        flatshading=True, name='Human Head'
    )
    traces.append(head_mesh)
    
    # Label
    traces.append(create_text_annotation(x_offset, y_offset, z_head + 400, "Person\n1.75m"))
    
    return traces

def create_car_mesh(x_offset, y_offset, z_start=0):
    """
    Create a simplified Honda Legend KC2 proxy.
    L~5000mm, W~1900mm, H~1450mm. Color: Silver.
    """
    traces = []
    
    # Car Body (Lower)
    # L=5000, W=1900, H=700
    L, W, H1 = 5000, 1900, 700
    lx, ly, lz = L/2, W/2, H1
    
    body_mesh = go.Mesh3d(
        x=[x_offset-lx, x_offset-lx, x_offset+lx, x_offset+lx, x_offset-lx, x_offset-lx, x_offset+lx, x_offset+lx],
        y=[y_offset-ly, y_offset+ly, y_offset+ly, y_offset-ly, y_offset-ly, y_offset+ly, y_offset+ly, y_offset-ly],
        z=[z_start, z_start, z_start, z_start, z_start+H1, z_start+H1, z_start+H1, z_start+H1],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='#C0C0C0', # Silver
        flatshading=True, name='Car Body'
    )
    traces.append(body_mesh)
    
    # Cabin (Upper)
    # L=2500, W=1600, H=600. Offset slightly back?
    L2, W2, H2 = 2500, 1600, 500
    lx2, ly2, lz2 = L2/2, W2/2, H2
    z_cabin = z_start + H1
    
    cabin_mesh = go.Mesh3d(
        x=[x_offset-lx2, x_offset-lx2, x_offset+lx2, x_offset+lx2, x_offset-lx2, x_offset-lx2, x_offset+lx2, x_offset+lx2],
        y=[y_offset-ly2, y_offset+ly2, y_offset+ly2, y_offset-ly2, y_offset-ly2, y_offset+ly2, y_offset+ly2, y_offset-ly2],
        z=[z_cabin, z_cabin, z_cabin, z_cabin, z_cabin+H2, z_cabin+H2, z_cabin+H2, z_cabin+H2],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='#A9A9A9', # Darker Grey Windows
        flatshading=True, name='Car Cabin'
    )
    traces.append(cabin_mesh)
    
    # Label
    traces.append(create_text_annotation(x_offset, y_offset, z_cabin + H2 + 400, "Sedan (Legend)\nL=5.0m"))
    
    return traces

def create_text_annotation(x, y, z, text):
    """Create a 3D text label with bright yellow colors for high visibility"""
    return go.Scatter3d(
        x=[x], y=[y], z=[z],
        mode='text',
        text=[text],
        textposition="middle right",
        textfont=dict(size=16, color="#FFFF00", family="Arial Black"), # Bright Yellow
        showlegend=False
    )

def generate_3d_preview(df: pd.DataFrame, title: str = "AxelOn Digital Twin"):
    fig = go.Figure()
    
    # 1. Parse Data
    def safe_float(val):
        try: return float(str(val).replace(",",""))
        except: return 0.0
    
    df['d_val'] = df['diameter_mm'].apply(safe_float)
    df['t_val'] = df['thickness_mm'].apply(safe_float)
    df['l_val'] = df['length_mm'].apply(safe_float)
    df['w_val'] = df['width_mm'].apply(safe_float)
    
    current_z = 0.0
    largest_d = 0
    
    # 2. Base Plate
    base_rows = df[df['name'].str.contains('Base', case=False) & df['type'].str.contains('Plate', case=False)]
    if not base_rows.empty:
        base = base_rows.iloc[0]
        l, w, t = base['l_val'], base['w_val'], base['t_val']
        if l > 0:
            # Metallic lighter gray for Base to contrast with dark bg
            mesh = create_box_mesh(l, w, t, current_z, color='#808080')
            if mesh: fig.add_trace(mesh)
            
            # Label - Offset heavily
            label_x = l/2 + 600
            label = create_text_annotation(label_x, w/2 + 100, t, f"Base PL\nt={t:.1f}")
            fig.add_trace(label)
            
            current_z += t
            
    else:
        current_z = 0 
        
    # 3. Pipes (Sorted)
    pipes = df[df['type'].str.contains('Pipe', case=False)].copy()
    
    if not pipes.empty:
        pipes = pipes.sort_values(by='d_val', ascending=False)
        largest_d = pipes.iloc[0]['d_val']
        
        for idx, row in pipes.iterrows():
            d, l = row['d_val'], row['l_val']
            
            if d > 0 and l > 0:
                is_bottom_pole = (d == largest_d)
                
                # Offset: Half Diameter + 550mm
                label_offset_x = d/2 + 550
                
                # Ground Level Protection Logic
                if is_bottom_pole and l > 1500:
                    protection_h = 1000.0
                    rest_h = l - protection_h
                    
                    # Protected Part
                    surf_bot = create_cylinder_mesh(d, protection_h, current_z, color='#5A708B')
                    fig.add_trace(surf_bot)
                    
                    # Top Part
                    surf_top = create_cylinder_mesh(d, rest_h, current_z + protection_h, color='#B8E0F6')
                    fig.add_trace(surf_top)
                    
                    label_text = f"Pipe D-<b>{d:.1f}</b>\nL={l:.0f}"
                    fig.add_trace(create_text_annotation(label_offset_x, 0, current_z + l/2, label_text))
                    
                    current_z += l
                else:
                    # Standard Pipe
                    surf = create_cylinder_mesh(d, l, current_z, color='#B8E0F6')
                    if surf: fig.add_trace(surf)
                    
                    label_text = f"D-<b>{d:.1f}</b> L={l:.0f}"
                    fig.add_trace(create_text_annotation(label_offset_x, 0, current_z + l/2, label_text))
                    
                    current_z += l
    
    # 4. Ribs
    ribs = df[df['name'].str.contains('Rib', case=False)]
    if not ribs.empty and largest_d > 0:
        rib = ribs.iloc[0]
        r_h = rib['l_val']
        r_w = rib['w_val']
        r_t = rib['t_val']
        
        try: count = int(safe_float(rib['count']))
        except: count = 4
        if count <= 0: count = 4
        
        radius = largest_d / 2.0
        z_rib_start = base_rows.iloc[0]['t_val'] if not base_rows.empty else 0
        
        for i in range(count):
            angle = i * (360.0 / count)
            # Lighter Ribs for visibility
            rib_mesh = create_rib_mesh(radius, r_w, r_h, r_t, z_rib_start, angle, color='#606060')
            fig.add_trace(rib_mesh)

    # 5. SCALE REFERENCE OBJECTS (NEW)
    # Human: Offset X = largest_d + 1500mm
    human_x = largest_d/2 + 1500
    human_traces = create_human_mesh(human_x, 0, z_start=0)
    for t in human_traces: fig.add_trace(t)
    
    # Car: Offset X = -(largest_d + 3000mm)
    car_x = -(largest_d/2 + 3000)
    car_traces = create_car_mesh(car_x, 0, z_start=0)
    for t in car_traces: fig.add_trace(t)

    # 6. Scene Settings - Dark Mode / Digital Twin
    bg_color = '#001f3f' # Deep Navy
    
    fig.update_layout(
        height=800,
        title={
            'text': title,
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24, color="white") # White Title
        },
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        scene=dict(
            aspectmode='data',
            # White Grid and Tick Labels
            xaxis=dict(title='', showgrid=True, gridcolor='rgba(255,255,255,0.15)', zeroline=False, showticklabels=False),
            yaxis=dict(title='', showgrid=True, gridcolor='rgba(255,255,255,0.15)', zeroline=False, showticklabels=False),
            zaxis=dict(
                title=dict(text='Height (mm)', font=dict(color='white', size=14)), 
                showgrid=True, 
                gridcolor='rgba(255,255,255,0.25)', 
                tickfont=dict(color='white', size=12)
            ),
            bgcolor=bg_color,
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0.2),
                eye=dict(x=2.5, y=2.5, z=1.5) # Zoom out slightly for car
            )
        ),
        margin=dict(l=0, r=0, b=0, t=80),
        showlegend=False,
        annotations=[
            dict(
                text="System Architecture by AxelOn Inc.",
                showarrow=False,
                xref="paper", yref="paper",
                x=1, y=0,
                xanchor='right', yanchor='bottom',
                # Crisp White Signature
                font=dict(size=14, color="white", family="Arial Black") 
            )
        ]
    )
    
    return fig
