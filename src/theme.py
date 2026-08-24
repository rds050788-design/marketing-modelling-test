"""Chart colour palette (CLAUDE.md section 6). Every colour the four
visuals use lives here -- change a colour once, here, not in src/charts.py.

The app pins an explicit dark theme in .streamlit/config.toml (Streamlit
otherwise follows each viewer's system preference, so the same app would
render light for some reviewers and dark for others). Every colour below is
chosen and contrast-checked against that pinned dark chart surface
(#1a1a19) -- not "designed to work on either," which is not physically
possible for a single flat colour: a near-white draft line has 17.4:1
contrast on dark but 1.03:1 on light (WCAG luminance contrast, computed
directly since no JS runtime was available in this environment to run the
data-viz skill's own validator). Pinning the theme is what makes "reads on
both light and dark" true in practice -- only one surface ever actually
renders for a viewer who accepts the app's default. A viewer who manually
overrides Streamlit's theme toggle back to light (Settings menu, top right)
is a known, unclosed gap -- Streamlit does not provide a way to lock this
from the server side.

Categorical scenario hues and the dark-surface ink tokens below are the
dark-mode steps from the data-viz skill's reference categorical palette
(pre-validated there for CVD-safe adjacent-pair separation and >=3:1
contrast on a #1a1a19 surface); the segment and marker-outline colours are
this app's own additions, contrast-checked against the same surface.
"""

# Categorical hues, dark-surface steps, in fixed assignment order -- never
# cycled or re-sorted. One scenario = one slot, in creation order. Contrast
# vs the #1a1a19 dark surface: slot 1 (blue) 4.79:1, all eight clear >=3:1
# per the data-viz skill's reference palette.
SCENARIO_COLORS = [
    "#3987e5",  # 1 blue
    "#d95926",  # 2 orange
    "#199e70",  # 3 aqua
    "#c98500",  # 4 yellow
    "#d55181",  # 5 magenta
    "#008300",  # 6 green
    "#9085e9",  # 7 violet
    "#e66767",  # 8 red
]

# Reserved for the live draft -- never a categorical slot, so it can never
# collide with a saved scenario's colour. Near-white: 17.4:1 contrast on
# the pinned dark surface, distinguished from every categorical hue by
# lightness alone (none of the eight above come close to white), on top of
# the thicker line and longdash pattern already distinguishing it.
DRAFT_COLOR = "#ffffff"

# Revenue-driver segment roles (not scenario identity) -- fixed regardless
# of which scenarios are on screen. Base is deliberately muted so the
# marketing/initiatives segments read as the smaller, secondary slivers
# they are -- the model's central finding, made visible.
BASE_SEGMENT_COLOR = "#c3c2b7"  # muted warm gray, 9.72:1 on dark surface
MARKETING_SEGMENT_COLOR = "#3987e5"  # categorical slot 1 (blue)
INITIATIVES_SEGMENT_COLOR = "#d95926"  # categorical slot 2 (orange)

# Chart chrome Streamlit's own dark Plotly template doesn't cover (explicit
# per-trace colours we set ourselves: line colours, marker outlines).
HISTORY_LINE_COLOR = "#898781"  # muted ink, 4.85:1 on dark surface -- de-emphasised actuals
MARKER_OUTLINE_COLOR = "#1a1a19"  # the dark chart surface itself -- halos a marker off its fill
