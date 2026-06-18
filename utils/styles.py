"""
Centralized styling configurations and Plotly templates for FormulaMind.
Provides consistent colors, fonts, and dark mode theme components.
"""

# F1 Team Color Palette (Official HEX codes)
TEAM_COLORS = {
    'mercedes': '#27F4D2',      # Neon Teal
    'ferrari': '#F91536',       # Racing Red
    'red bull': '#3671C6',      # Royal Blue
    'mclaren': '#F58020',       # Papaya Orange
    'aston martin': '#229971',  # Racing Green
    'alpine': '#0093CC',        # Light Blue
    'williams': '#37BEDD',      # Cyan
    'haas': '#B6BABD',          # White/Silver
    'sauber': '#52E252',        # Neon Green
    'rb': '#6692FF',            # Visa Cash App RB Blue
}

# Tire Compound Colors (Official Pirelli color scheme)
TIR_COMPOUND_COLORS = {
    'SOFT': '#FF3333',          # Red
    'MEDIUM': '#FFD300',        # Yellow
    'HARD': '#FFFFFF',          # White
    'INTERMEDIATE': '#39FF14',   # Green
    'WET': '#00A0FF',           # Blue
    'UNKNOWN': '#888888'
}

# Theme Color Constants for Premium Dark Theme
BG_DARK = '#0F1219'          # Slate Black
CARD_DARK = '#161B26'        # Dark Card Background
TEXT_LIGHT = '#F1F5F9'       # Off-white
TEXT_MUTED = '#94A3B8'       # Cool Gray
ACCENT_CYAN = '#00E5FF'      # Cyber Cyan
ACCENT_PINK = '#FF007F'      # Cyber Pink

FONT_FAMILY = "Inter, Montserrat, Roboto, Helvetica, Arial, sans-serif"

def apply_premium_layout(fig, title=""):
    """
    Applies a premium, dark glassmorphism layout to any Plotly figure.
    """
    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 18, 'color': TEXT_LIGHT, 'family': FONT_FAMILY}
        },
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent paper
        plot_bgcolor='rgba(22, 27, 38, 0.5)',  # Translucent dark grid background
        font=dict(color=TEXT_LIGHT, family=FONT_FAMILY),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=CARD_DARK,
            font_size=12,
            font_family=FONT_FAMILY,
            bordercolor=TEXT_MUTED
        ),
        xaxis=dict(
            gridcolor='#222938',
            linecolor='#334155',
            linewidth=1,
            zeroline=False,
            tickfont=dict(color=TEXT_MUTED),
            title_font=dict(color=TEXT_LIGHT)
        ),
        yaxis=dict(
            gridcolor='#222938',
            linecolor='#334155',
            linewidth=1,
            zeroline=False,
            tickfont=dict(color=TEXT_MUTED),
            title_font=dict(color=TEXT_LIGHT)
        ),
        legend=dict(
            bgcolor='rgba(15, 18, 25, 0.8)',
            bordercolor='#2D3748',
            borderwidth=1,
            font=dict(size=10, color=TEXT_LIGHT)
        )
    )
    return fig  