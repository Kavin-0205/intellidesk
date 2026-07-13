APP_STYLE = """
QMainWindow{
    background:#F5F7FA;
}

QWidget{
    background:#F5F7FA;
    font-family:Segoe UI;
    font-size:12px;
}

QListWidget{
    background:white;
    border:none;
    border-radius:12px;
    padding:8px;
}

QListWidget::item{
    padding:12px;
    border-radius:8px;
}

QListWidget::item:selected{
    background:#4F8EF7;
    color:white;
}

QListWidget::item:hover{
    background:#E6F0FF;
}

QFrame#dashboardCard{
    background:white;
    border-radius:15px;
    border:1px solid #E0E0E0;
}

QLabel#cardTitle{
    font-size:15px;
    font-weight:bold;
    color:#555;
}

QLabel#cardValue{
    font-size:28px;
    font-weight:bold;
    color:#222;
}
"""