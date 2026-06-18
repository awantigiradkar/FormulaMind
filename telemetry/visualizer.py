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