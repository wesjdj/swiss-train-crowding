"""SDSC chart palette, defined once for matplotlib and plotly."""

CATEGORICAL = ["#26235c", "#73a235", "#b34a00", "#56b4e9", "#cc79a7"]
MUTED = "#b8b8b8"
GRID = "#e5e5e5"
LEVEL_COLORS = {1: "#dddeec", 2: "#7a7ab5", 3: "#26235c"}
DIVERGING = ["#26235c", "#7a7ab5", "#f0eeeb", "#cf7d42", "#b34a00"]
SEQUENTIAL_CMAP = "viridis"


def use_matplotlib() -> None:
    """Apply the SDSC style to matplotlib."""
    import matplotlib as mpl

    mpl.rcParams.update({
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
        "image.cmap": SEQUENTIAL_CMAP,
        "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": GRID, "axes.edgecolor": "#848484",
        "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 12, "figure.dpi": 110, "figure.figsize": (10, 4.5),
    })


def use_plotly() -> None:
    """Register the SDSC plotly template and make it the default."""
    import plotly.graph_objects as go
    import plotly.io as pio

    pio.templates["sdsc"] = go.layout.Template(layout={
        "colorway": CATEGORICAL,
        "colorscale": {"sequential": "Viridis"},
        "font": {"size": 12},
        "xaxis": {"showgrid": False},
        "yaxis": {"gridcolor": GRID},
        "plot_bgcolor": "white",
    })
    pio.templates.default = "sdsc"
