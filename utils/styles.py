"""
FormulaMind - Premium Styling Module
Official F1 team colors and Plotly layout helpers.
"""

# Official F1 Team Colors (2023-2024 Season)

# These hex codes match the exact colors used in F1 TV broadcasts.
# Source: Official FIA technical regulations & team brand guidelines.

TEAM_COLORS = {
    "Red Bull Racing":    "#3671C6",
    "Ferrari":            "#E8002D",
    "Mercedes":           "#27F4D2",
    "McLaren":            "#FF8000",
    "Aston Martin":       "#229971",
    "Alpine":             "#FF87BC",
    "Williams":           "#64C4FF",
    "AlphaTauri":         "#6692FF",
    "Alfa Romeo":         "#C92D4B",
    "Haas F1 Team":       "#B6BABD",
}

# Short-name mapping (FastF1 uses 3-letter driver codes)
DRIVER_TEAM = {
    "VER": "Red Bull Racing",
    "PER": "Red Bull Racing",
    "LEC": "Ferrari",
    "SAI": "Ferrari",
    "HAM": "Mercedes",
    "RUS": "Mercedes",
    "NOR": "McLaren",
    "PIA": "McLaren",
    "ALO": "Aston Martin",
    "STR": "Aston Martin",
    "GAS": "Alpine",
    "OCO": "Alpine",
    "ALB": "Williams",
    "SAR": "Williams",
    "TSU": "AlphaTauri",
    "DEV": "AlphaTauri",
    "BOT": "Alfa Romeo",
    "ZHO": "Alfa Romeo",
    "MAG": "Haas F1 Team",
    "HUL": "Haas F1 Team",
}

# Premium dark theme colors for our dashboard
BACKGROUND_COLOR = "#0F1117"
GRID_COLOR = "#1E2130"
TEXT_COLOR = "#E0E0E0"
ACCENT_COLOR = "#FF1E00"  # F1 signature red


def get_driver_color(driver_code):
    """
    The official team color for a driver.

    Args:
        driver_code (str): 3-letter driver code, e.g. 'VER', 'HAM'

    Returns:
        str: Hex color string, e.g. '#3671C6'
    """
    team = DRIVER_TEAM.get(driver_code, None)
    if team:
        return TEAM_COLORS.get(team, "#FFFFFF")
    return "#FFFFFF"  # Default white if unknown driver


def apply_premium_layout(fig, title=""):
    """
    Apply premium dark theme to any Plotly figure.
    This gives every chart a consistent, broadcast-quality look.

    Args:
        fig: A Plotly figure object
        title (str): Chart title text
    """
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, color=TEXT_COLOR, family="Arial Black"),
            x=0.5,           # Center the title
            xanchor="center",
        ),
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=BACKGROUND_COLOR,
        font=dict(color=TEXT_COLOR, family="Arial"),
        legend=dict(
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor=GRID_COLOR,
            borderwidth=1,
            font=dict(color=TEXT_COLOR),
        ),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            zerolinecolor=GRID_COLOR,
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            zerolinecolor=GRID_COLOR,
        ),
        margin=dict(l=60, r=30, t=60, b=50),
    )
    return fig