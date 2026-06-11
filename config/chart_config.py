"""Chart rendering configuration for ColtraDataAi.

Centralises all chart dimension, scale and theme defaults so the gallery,
dashboard and export surfaces all produce consistent output without
duplicating constants.
"""

# PNG export dimensions (used by Kaleido for Excel/PDF embedding)
CHART_EXPORT = {
    "width":  760,
    "height": 400,
    "scale":  2,     # 2× for retina-quality embedding
}

CHART_ASPECT_RATIO = CHART_EXPORT["width"] / CHART_EXPORT["height"]

# Live Plotly chart heights (pixels) for the Streamlit dashboard
CHART_HEIGHTS = {
    "bar":         380,
    "donut":       360,
    "histogram":   340,
    "heatmap":     420,
    "line":        380,
    "area":        380,
}

# Gallery auto-generation limits
GALLERY = {
    "max_numeric":     3,   # max numeric distribution charts
    "max_categorical": 3,   # max categorical frequency charts
    "top_n_categories": 8,  # categories shown in frequency bar charts
    "top_n_values":     5,  # values shown in top/bottom tables
}

# Plotly layout defaults applied by _premium_theme()
THEME = {
    "font_family":   "Segoe UI, Helvetica, Arial, sans-serif",
    "font_size":     11,
    "font_colour":   "#33414E",
    "title_size":    14,
    "tick_size":     10,
    "tick_colour":   "#657286",
    "grid_colour":   "#F0F4F8",
    "axis_colour":   "#E6ECF0",
    "bg_colour":     "#FFFFFF",
    "hover_bg":      "white",
    "hover_border":  "#E6ECF0",
    "margin":        {"l": 44, "r": 30, "t": 64, "b": 52},
}

# Colour scales used in heatmaps and continuous colour bars
COLOUR_SCALES = {
    "quality":  ["#D7F3F7", "#D9E1F2", "#1F4E79"],
    "risk":     ["#2ECC71", "#F39C12", "#E74C3C"],
    "neutral":  ["#F8FAFC", "#D9E1F2", "#1F4E79"],
}
