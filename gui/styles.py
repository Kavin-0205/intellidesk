"""
IntelliDesk Premium Dark Theme Stylesheet.
Uses a deep navy + electric blue palette with glassmorphism card effects.
"""

DARK_THEME = """
/* ===== ROOT ===== */
QMainWindow, QWidget {
    background-color: #0D1117;
    color: #E6EDF3;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ===== SIDEBAR ===== */
QWidget#sidebar {
    background-color: #161B22;
    border-right: 1px solid #30363D;
}

QPushButton#navBtn {
    background: transparent;
    color: #8B949E;
    border: none;
    padding: 14px 18px;
    text-align: left;
    font-size: 13px;
    border-radius: 10px;
    margin: 2px 8px;
}

QPushButton#navBtn:hover {
    background: #21262D;
    color: #E6EDF3;
}

QPushButton#navBtn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1F6FEB, stop:1 #388BFD);
    color: white;
    font-weight: bold;
}

/* ===== DASHBOARD CARDS ===== */
QFrame#dashCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #161B22, stop:1 #1A2030);
    border: 1px solid #30363D;
    border-radius: 16px;
    padding: 8px;
}

QLabel#cardIcon {
    font-size: 28px;
}

QLabel#cardTitle {
    font-size: 12px;
    color: #8B949E;
    font-weight: 500;
}

QLabel#cardValue {
    font-size: 26px;
    font-weight: bold;
    color: #58A6FF;
}

QLabel#cardSub {
    font-size: 11px;
    color: #484F58;
}

/* ===== VOICE PAGE ===== */
QWidget#voicePage {
    background: transparent;
}

QFrame#voiceOrb {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
        stop:0 #1F6FEB, stop:0.6 #0D1117, stop:1 #0D1117);
    border: 2px solid #1F6FEB;
    border-radius: 80px;
}

QLabel#statusLabel {
    font-size: 16px;
    color: #8B949E;
    font-weight: 500;
}

QLabel#transcriptLabel {
    font-size: 13px;
    color: #8B949E;
    padding: 8px 16px;
    background: #161B22;
    border-radius: 10px;
    border: 1px solid #30363D;
}

QPushButton#micBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1F6FEB, stop:1 #388BFD);
    color: white;
    border: none;
    border-radius: 32px;
    font-size: 22px;
    font-weight: bold;
    min-width: 64px;
    max-width: 64px;
    min-height: 64px;
    max-height: 64px;
}

QPushButton#micBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #388BFD, stop:1 #58A6FF);
}

QPushButton#micBtn:pressed {
    background: #0F3770;
}

/* ===== CHAT BUBBLE AREA ===== */
QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: #161B22;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #30363D;
    border-radius: 3px;
}

/* ===== HISTORY PAGE ===== */
QListWidget {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 6px;
    color: #E6EDF3;
}

QListWidget::item {
    padding: 10px 14px;
    border-radius: 8px;
    color: #C9D1D9;
}

QListWidget::item:selected {
    background: #1F6FEB;
    color: white;
}

QListWidget::item:hover {
    background: #21262D;
}

/* ===== PAGE HEADERS ===== */
QLabel#pageHeader {
    font-size: 22px;
    font-weight: bold;
    color: #E6EDF3;
    padding: 4px 0;
}

QLabel#pageSubtitle {
    font-size: 13px;
    color: #8B949E;
    padding-bottom: 8px;
}

/* ===== SECTION CARDS ===== */
QFrame#sectionCard {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 14px;
    padding: 16px;
}

/* ===== PROGRESS BAR ===== */
QProgressBar {
    background: #21262D;
    border: none;
    border-radius: 4px;
    height: 6px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1F6FEB, stop:1 #58A6FF);
    border-radius: 4px;
}

/* ===== TOOL BAR SEPARATOR ===== */
QFrame#divider {
    background: #30363D;
    max-height: 1px;
}
"""

APP_STYLE = DARK_THEME