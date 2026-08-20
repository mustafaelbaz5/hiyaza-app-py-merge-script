"""All colors, fonts, and spacing constants for the GUI. No logic here."""

from pathlib import Path

# Primary — agricultural green
PRIMARY_900 = "#1B5E20"
PRIMARY_700 = "#388E3C"
PRIMARY_500 = "#66BB6A"
PRIMARY_100 = "#E8F5E9"
PRIMARY_50 = "#F1F8E9"

# Neutral
NEUTRAL_900 = "#212121"
NEUTRAL_700 = "#616161"
NEUTRAL_300 = "#E0E0E0"
NEUTRAL_100 = "#F5F5F5"
NEUTRAL_50 = "#FAFAFA"
WHITE = "#FFFFFF"

# Semantic
SUCCESS = "#2E7D32"
WARNING = "#F57F17"
ERROR = "#C62828"
INFO = "#1565C0"

# Accent
ACCENT_GOLD = "#F9A825"

# Typography
FONT_FAMILY = "Arial"

FONT_TITLE = (FONT_FAMILY, 20, "bold")
FONT_HEADING = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_SMALL = (FONT_FAMILY, 10)
FONT_MONO = ("Courier New", 11)

# Spacing
PAD_XL = 32
PAD_L = 24
PAD_M = 16
PAD_S = 8
PAD_XS = 4

RADIUS_CARD = 12
RADIUS_BUTTON = 8
RADIUS_BADGE = 6

# Window
WINDOW_TITLE = "دمج بيانات الحيازات الزراعية"
WINDOW_WIDTH = 720
WINDOW_HEIGHT = 560

# Default output locations, keyed by association type
OUTPUT_BASE_DIRS = {
    "credit": Path(r"D:\WORK\hiyaza_work\app_data\ائتمان"),
    "reform": Path(r"D:\WORK\hiyaza_work\app_data\اصلاح"),
}
