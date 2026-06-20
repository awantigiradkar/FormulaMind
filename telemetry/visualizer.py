"""
Telemetry Visualizer
Generates premium-level interactive Plotly figures for telemetry analysis.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from utils.styles import TEAM_COLORS, apply_premium_layout, ACCENT_CYAN, ACCENT_PINK, TEXT_LIGHT

def plot_speed_comparison(df_aligned, metadata):
    """
    Creates a dual-plot chart:
    1. Speed comparison trace (km/h vs Distance) for both drivers.
    2. Delta time trace (seconds vs Distance) showing time gains/losses.
    """
    driver_a = metadata['driver_a']
    driver_b = metadata['driver_b']
    
    color_a = TEAM_COLORS.get(metadata['team_a'].lower(), ACCENT_CYAN)
    color_b = TEAM_COLORS.get(metadata['team_b'].lower(), ACCENT_PINK)
    
    # If drivers are in the same team (same colors), shift driver B to pink for contrast
    if color_a == color_b:
        color_b = ACCENT_PINK
        
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=("Speed Trace Comparison", f"Time Delta ({driver_a} vs {driver_b})")
    )
    
    # Speed trace Driver A
    fig.add_trace(
        go.Scatter(
            x=df_aligned['Distance'], 
            y=df_aligned[f'Speed_{driver_a}'],
            name=f"{driver_a} ({metadata['lap_time_a']:.3f}s)",
            line=dict(color=color_a, width=2),
            hovertemplate="%{y:.1f} km/h"
        ),
        row=1, col=1
    )
    
    # Speed trace Driver B
    fig.add_trace(
        go.Scatter(
            x=df_aligned['Distance'], 
            y=df_aligned[f'Speed_{driver_b}'],
            name=f"{driver_b} ({metadata['lap_time_b']:.3f}s)",
            line=dict(color=color_b, width=2, dash='dash'),
            hovertemplate="%{y:.1f} km/h"
        ),
        row=1, col=1
    )
    
    # Time Delta (Negative means Driver A is faster/ahead)
    fig.add_trace(
        go.Scatter(
            x=df_aligned['Distance'], 
            y=df_aligned['DeltaTime'],
            name=f"Delta (t_{driver_a} - t_{driver_b})",
            line=dict(color='#A855F7', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(168, 85, 247, 0.15)',
            hovertemplate="%{y:+.3f}s"
        ),
        row=2, col=1
    )
    
    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
    fig.update_yaxes(title_text="Gap (s)", row=2, col=1)
    fig.update_xaxes(title_text="Distance (m)", row=2, col=1)
    
    # Draw DRS zones as translucent cyan background bands on the speed chart
    try:
        def get_drs_ranges(df, driver_col):
            ranges = []
            active = df[driver_col] >= 10
            in_range = False
            start_dist = 0
            for idx, row in df.iterrows():
                if active[idx] and not in_range:
                    start_dist = row['Distance']
                    in_range = True
                elif not active[idx] and in_range:
                    ranges.append((start_dist, row['Distance']))
                    in_range = False
            if in_range:
                ranges.append((start_dist, df['Distance'].iloc[-1]))
            return ranges

        # Highlight DRS zones for Driver A
        drs_ranges = get_drs_ranges(df_aligned, f'DRS_{driver_a}')
        for r_start, r_end in drs_ranges:
            fig.add_vrect(
                x0=r_start, x1=r_end,
                fillcolor="rgba(0, 229, 255, 0.05)",  # Translucent neon cyan
                layer="below", line_width=0,
                row=1, col=1
            )
    except Exception:
        pass
        
    fig = apply_premium_layout(fig, f"Telemetry Comparison: {driver_a} vs {driver_b}")
    
    for i in range(len(fig.layout.annotations)):
        fig.layout.annotations[i].font.size = 13
        fig.layout.annotations[i].font.color = TEXT_LIGHT
        
    return fig

def plot_pedal_analysis(df_aligned, metadata):
    """
    Overlays throttle (0-100%) and brake (binary) plots for both drivers.
    """
    driver_a = metadata['driver_a']
    driver_b = metadata['driver_b']
    
    color_a = TEAM_COLORS.get(metadata['team_a'].lower(), ACCENT_CYAN)
    color_b = TEAM_COLORS.get(metadata['team_b'].lower(), ACCENT_PINK)
    
    if color_a == color_b:
        color_b = ACCENT_PINK
        
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
        row_heights=[0.5, 0.5],
        subplot_titles=("Throttle Inputs (%)", "Brake Inputs")
    )
    
    # Throttle Driver A
    fig.add_trace(
        go.Scatter(
            x=df_aligned['Distance'], 
            y=df_aligned[f'Throttle_{driver_a}'],
            name=f"{driver_a} Throttle",
            line=dict(color=color_a, width=2),
            hovertemplate="%{y:.0f}%"
        ),
        row=1, col=1
    )
    
    # Throttle Driver B
    fig.add_trace(
        go.Scatter(
            x=df_aligned['Distance'], 
            y=df_aligned[f'Throttle_{driver_b}'],
            name=f"{driver_b} Throttle",
            line=dict(color=color_b, width=2, dash='dash'),
            hovertemplate="%{y:.0f}%"
        ),
        row=1, col=1
    )
    
    # Brake Driver A
    fig.add_trace(
        go.Scatter(
            x=df_aligned['Distance'], 
            y=df_aligned[f'Brake_{driver_a}'],
            name=f"{driver_a} Brake",
            line=dict(color=color_a, width=1.5),
            hovertemplate="%{y:.0f}"
        ),
        row=2, col=1
    )
    
    # Brake Driver B
    fig.add_trace(
        go.Scatter(
            x=df_aligned['Distance'], 
            y=df_aligned[f'Brake_{driver_b}'],
            name=f"{driver_b} Brake",
            line=dict(color=color_b, width=1.5, dash='dash'),
            hovertemplate="%{y:.0f}"
        ),
        row=2, col=1
    )
    
    fig.update_yaxes(title_text="Throttle %", range=[-5, 105], row=1, col=1)
    fig.update_yaxes(title_text="Brake Active (0/1)", range=[-0.1, 1.1], tickvals=[0, 1], row=2, col=1)
    fig.update_xaxes(title_text="Distance (m)", row=2, col=1)
    
    fig = apply_premium_layout(fig, f"Pedal Inputs: {driver_a} vs {driver_b}")
    
    for i in range(len(fig.layout.annotations)):
        fig.layout.annotations[i].font.size = 13
        fig.layout.annotations[i].font.color = TEXT_LIGHT
        
    return fig

def plot_gear_shifts(df_aligned, metadata):
    """
    Plots the gear shifts of both drivers along the track distance.
    Uses step lines ('hv') to reflect gear changes correctly.
    """
    driver_a = metadata['driver_a']
    driver_b = metadata['driver_b']
    
    color_a = TEAM_COLORS.get(metadata['team_a'].lower(), ACCENT_CYAN)
    color_b = TEAM_COLORS.get(metadata['team_b'].lower(), ACCENT_PINK)
    
    if color_a == color_b:
        color_b = ACCENT_PINK
        
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_aligned['Distance'],
        y=df_aligned[f'Gear_{driver_a}'],
        name=f"{driver_a} Gear",
        mode='lines',
        line=dict(color=color_a, width=2, shape='hv'),
        hovertemplate="Gear %{y}"
    ))
    
    fig.add_trace(go.Scatter(
        x=df_aligned['Distance'],
        y=df_aligned[f'Gear_{driver_b}'],
        name=f"{driver_b} Gear",
        mode='lines',
        line=dict(color=color_b, width=2, dash='dash', shape='hv'),
        hovertemplate="Gear %{y}"
    ))
    
    fig.update_yaxes(title_text="Gear", tickvals=list(range(1, 9)))
    fig.update_xaxes(title_text="Distance (m)")
    
    fig = apply_premium_layout(fig, f"Gear Profile Comparison: {driver_a} vs {driver_b}")
    return fig

def plot_track_dominance(session, driver_a, driver_b, lap_a=None, lap_b=None):
    """
    Generates a 2D map of the track layout, color-coded by who was faster at each point.
    """
    driver_laps_a = session.laps.pick_drivers(driver_a)
    driver_laps_b = session.laps.pick_drivers(driver_b)
    
    lap_obj_a = driver_laps_a.pick_fastest() if lap_a is None else driver_laps_a[driver_laps_a['LapNumber'] == lap_a].iloc[0]
    lap_obj_b = driver_laps_b.pick_fastest() if lap_b is None else driver_laps_b[driver_laps_b['LapNumber'] == lap_b].iloc[0]
    
    tel_a = lap_obj_a.get_telemetry()
    tel_b = lap_obj_b.get_telemetry()
    
    if 'X' not in tel_a.columns or 'Y' not in tel_a.columns:
        fig = go.Figure()
        fig.add_annotation(text="Position coordinates (X, Y) telemetry unavailable for this session.",
                           xref="paper", yref="paper", showarrow=False, font_size=14)
        fig = apply_premium_layout(fig, "Track Dominance Map (Unavailable)")
        return fig
        
    points = 1200
    max_distance = min(tel_a['Distance'].max(), tel_b['Distance'].max())
    distance_grid = np.linspace(0, max_distance, points)
    
    x_avg = (np.interp(distance_grid, tel_a['Distance'], tel_a['X']) + 
             np.interp(distance_grid, tel_b['Distance'], tel_b['X'])) / 2.0
    y_avg = (np.interp(distance_grid, tel_a['Distance'], tel_a['Y']) + 
             np.interp(distance_grid, tel_b['Distance'], tel_b['Y'])) / 2.0
             
    speed_a = np.interp(distance_grid, tel_a['Distance'], tel_a['Speed'])
    speed_b = np.interp(distance_grid, tel_b['Distance'], tel_b['Speed'])
    
    dominance = np.where(speed_a > speed_b, 1, 0)
    
    color_a = TEAM_COLORS.get(session.get_driver(driver_a)['TeamName'].lower(), ACCENT_CYAN)
    color_b = TEAM_COLORS.get(session.get_driver(driver_b)['TeamName'].lower(), ACCENT_PINK)
    
    if color_a == color_b:
        color_b = ACCENT_PINK
        
    fig = go.Figure()
    
    # Gray background track line
    fig.add_trace(go.Scatter(
        x=x_avg, y=y_avg,
        mode='lines',
        line=dict(color='#2D3748', width=8),
        hoverinfo='skip',
        showlegend=False
    ))
    
    # Driver A dominant points
    fig.add_trace(go.Scatter(
        x=x_avg[dominance == 1],
        y=y_avg[dominance == 1],
        mode='markers',
        marker=dict(color=color_a, size=4),
        name=f"{driver_a} Faster",
        hovertext=f"{driver_a} Dominant Point",
        hoverinfo='text'
    ))
    
    # Driver B dominant points
    fig.add_trace(go.Scatter(
        x=x_avg[dominance == 0],
        y=y_avg[dominance == 0],
        mode='markers',
        marker=dict(color=color_b, size=4),
        name=f"{driver_b} Faster",
        hovertext=f"{driver_b} Dominant Point",
        hoverinfo='text'
    ))
    
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", scaleratio=1)
    
    fig = apply_premium_layout(fig, f"Track Dominance Map: {driver_a} vs {driver_b}")
    return fig

def plot_driver_scorecard(df_aligned, metadata):
    """
    Analyzes raw telemetry vectors, extracts performance scores,
    and plots a comparative Radar (Spider) chart for both drivers.
    """
    driver_a = metadata['driver_a']
    driver_b = metadata['driver_b']
    
    color_a = TEAM_COLORS.get(metadata['team_a'].lower(), ACCENT_CYAN)
    color_b = TEAM_COLORS.get(metadata['team_b'].lower(), ACCENT_PINK)
    
    if color_a == color_b:
        color_b = ACCENT_PINK
        
    scores = {}
    
    # Extract ratings for both drivers
    for driver in [driver_a, driver_b]:
        # 1. Straight-Line Speed (Max Speed relative to 330 km/h benchmark)
        max_speed = df_aligned[f'Speed_{driver}'].max()
        score_speed = np.clip((max_speed - 260) / (340 - 260) * 40 + 60, 50, 100)
        
        # 2. Throttle Application (Average throttle across the whole lap)
        avg_throttle = df_aligned[f'Throttle_{driver}'].mean()
        score_throttle = np.clip((avg_throttle - 40) / (85 - 40) * 50 + 50, 50, 100)
        
        # 3. Braking Aggression (Rate of deceleration when braking is active)
        brake_active = df_aligned[df_aligned[f'Brake_{driver}'] > 0.5]
        if len(brake_active) > 2:
            decels = -np.diff(df_aligned[f'Speed_{driver}'])
            decels_braking = decels[df_aligned[f'Brake_{driver}'].iloc[:-1] > 0.5]
            avg_decel = decels_braking.mean() if len(decels_braking) > 0 else 0.5
            score_braking = np.clip((avg_decel - 0.1) / (1.5 - 0.1) * 50 + 50, 50, 100)
        else:
            score_braking = 75.0  # Fallback baseline
            
        # 4. Corner Apex Speed (Average of bottom 15% slowest speed values)
        slow_points = np.percentile(df_aligned[f'Speed_{driver}'], 15)
        score_apex = np.clip((slow_points - 60) / (120 - 60) * 50 + 50, 50, 100)
        
        # 5. Gear Shift Efficiency (Ideal number of gear changes benchmarked)
        gear_changes = np.sum(np.abs(np.diff(df_aligned[f'Gear_{driver}'])))
        score_gears = np.clip(100 - (gear_changes - 35) * 1.1, 50, 100)
        
        scores[driver] = [score_speed, score_braking, score_throttle, score_apex, score_gears]
        
    # Categories of the Radar spider web
    categories = [
        'Straight-Line Speed', 
        'Braking Aggression', 
        'Throttle Application', 
        'Corner Apex Speed', 
        'Gear Shift Efficiency'
    ]
    
    fig = go.Figure()
    
    # Radar trace for Driver A
    fig.add_trace(go.Scatterpolar(
        r=scores[driver_a],
        theta=categories,
        fill='toself',
        fillcolor=f"rgba({int(color_a[1:3], 16)}, {int(color_a[3:5], 16)}, {int(color_a[5:7], 16)}, 0.2)" if len(color_a)==7 else "rgba(0, 229, 255, 0.2)",
        name=driver_a,
        line=dict(color=color_a, width=2)
    ))
    
    # Radar trace for Driver B
    fig.add_trace(go.Scatterpolar(
        r=scores[driver_b],
        theta=categories,
        fill='toself',
        fillcolor=f"rgba({int(color_b[1:3], 16)}, {int(color_b[3:5], 16)}, {int(color_b[5:7], 16)}, 0.2)" if len(color_b)==7 else "rgba(255, 0, 127, 0.2)",
        name=driver_b,
        line=dict(color=color_b, width=2)
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[50, 100], gridcolor='#222938', color='#94A3B8'),
            angularaxis=dict(gridcolor='#222938', color='#F1F5F9'),
            bgcolor='rgba(0, 0, 0, 0)'
        ),
        showlegend=True
    )
    
    fig = apply_premium_layout(fig, f"Driver Style Signature: {driver_a} vs {driver_b}")
    return fig

def detect_corners(df_aligned, driver_a):
    """
    Dynamically finds speed local minima (apexes) on the track speed trace.
    Returns a list of dictionaries with indices, distance coordinates, and speeds.
    """
    speed = df_aligned[f'Speed_{driver_a}'].values
    distance = df_aligned['Distance'].values
    
    # 5-point moving average to smooth trace sensor noise
    smoothed = np.convolve(speed, np.ones(5)/5, mode='same')
    
    apexes = []
    # Scan trace for local minima (corners are generally under 230 km/h)
    for i in range(15, len(smoothed) - 15):
        if smoothed[i] < 230:
            window = smoothed[i-15:i+16]
            if smoothed[i] == min(window):
                # Ensure corners are spaced at least 180 meters apart
                if not apexes or (distance[i] - apexes[-1]['distance'] > 180):
                    apexes.append({
                        'index': i,
                        'distance': distance[i],
                        'speed': speed[i]
                    })
    return apexes

def plot_corner_performance(df_aligned, metadata, apex_info):
    """
    Overlays telemetry focused on a +/- 100m window around the chosen corner apex.
    Calculates braking points, apex speeds, and throttle pick-up points.
    """
    driver_a = metadata['driver_a']
    driver_b = metadata['driver_b']
    
    color_a = TEAM_COLORS.get(metadata['team_a'].lower(), ACCENT_CYAN)
    color_b = TEAM_COLORS.get(metadata['team_b'].lower(), ACCENT_PINK)
    
    if color_a == color_b:
        color_b = ACCENT_PINK
        
    apex_dist = apex_info['distance']
    
    # Slice telemetry around the corner (+/- 100 meters)
    corner_df = df_aligned[(df_aligned['Distance'] >= apex_dist - 100) & 
                           (df_aligned['Distance'] <= apex_dist + 100)].copy()
    
    stats = {}
    for driver in [driver_a, driver_b]:
        # Apex Speed
        min_speed = corner_df[f'Speed_{driver}'].min()
        apex_idx = corner_df[f'Speed_{driver}'].idxmin()
        apex_distance = corner_df.loc[apex_idx, 'Distance']
        
        # Braking Point: first point before apex where driver brakes
        pre_apex = corner_df[corner_df['Distance'] <= apex_distance]
        brakes = pre_apex[pre_apex[f'Brake_{driver}'] > 0.5]
        brake_dist = brakes['Distance'].iloc[0] if not brakes.empty else (apex_distance - 45)
        
        # Throttle Pick-Up: first point after apex where throttle > 30%
        post_apex = corner_df[corner_df['Distance'] >= apex_distance]
        throttles = post_apex[post_apex[f'Throttle_{driver}'] > 30]
        throttle_dist = throttles['Distance'].iloc[0] if not throttles.empty else (apex_distance + 35)
        
        stats[driver] = {
            'apex_speed': min_speed,
            'brake_point': brake_dist,
            'throttle_point': throttle_dist
        }
        
    # Stacked plots: Speed trace on top, Throttle inputs on bottom
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08, 
        row_heights=[0.6, 0.4]
    )
    
    # Speed traces
    fig.add_trace(go.Scatter(x=corner_df['Distance'], y=corner_df[f'Speed_{driver_a}'], name=f"{driver_a} Speed", line=dict(color=color_a, width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=corner_df['Distance'], y=corner_df[f'Speed_{driver_b}'], name=f"{driver_b} Speed", line=dict(color=color_b, width=2.5, dash='dash')), row=1, col=1)
    
    # Braking points vertical indicator lines
    fig.add_vline(x=stats[driver_a]['brake_point'], line=dict(color=color_a, width=1.5, dash='dot'), row=1, col=1)
    fig.add_vline(x=stats[driver_b]['brake_point'], line=dict(color=color_b, width=1.5, dash='dot'), row=1, col=1)
    
    # Throttle traces
    fig.add_trace(go.Scatter(x=corner_df['Distance'], y=corner_df[f'Throttle_{driver_a}'], name=f"{driver_a} Throttle %", line=dict(color=color_a, width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=corner_df['Distance'], y=corner_df[f'Throttle_{driver_b}'], name=f"{driver_b} Throttle %", line=dict(color=color_b, width=1.5, dash='dash')), row=2, col=1)
    
    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
    fig.update_yaxes(title_text="Throttle %", row=2, col=1)
    fig.update_xaxes(title_text="Distance (m)", row=2, col=1)
    
    fig = apply_premium_layout(fig, f"ATLAS Performance Zoom: Turn Apex at {int(apex_dist)}m")
    
    return fig, stats