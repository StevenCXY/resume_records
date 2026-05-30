import sys
import json
import os
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                               QLabel, QLineEdit, QPushButton, QListWidget,
                               QListWidgetItem, QGraphicsDropShadowEffect, QFrame,
                               QTabWidget, QDialog)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QColor

import pyqtgraph as pg

DATA_FILE = "resume_records.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"tasks": [], "records": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 独立任务数据看板 (弹窗 Dialog)
# ==========================================
class TaskDashboardDialog(QDialog):
    def __init__(self, goal, remark, parent=None):
        super().__init__(parent)
        self.goal = goal
        self.remark = remark
        self.setWindowTitle(f"Stats: {goal}")
        self.resize(500, 400)
        
        # 继承主窗口的极简风格
        self.setStyleSheet("""
            QDialog { background-color: #F5F5F7; font-family: -apple-system, sans-serif; }
            QLabel { color: #1D1D1F; }
        """)
        
        self.setup_ui()
        self.load_task_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题栏
        title = QLabel(f"{self.goal}")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        subtitle = QLabel(f"渠道/备注: {self.remark}")
        subtitle.setStyleSheet("font-size: 14px; color: #86868B; margin-bottom: 10px;")
        
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # 顶层数据卡片
        top_layout = QHBoxLayout()
        self.total_lbl = QLabel("Task Total\n0")
        self.total_lbl.setStyleSheet("font-size: 18px; font-weight: bold; background: white; border-radius: 12px; padding: 15px; text-align: center;")
        self.total_lbl.setAlignment(Qt.AlignCenter)
        
        self.today_lbl = QLabel("Today\n0")
        self.today_lbl.setStyleSheet("font-size: 18px; font-weight: bold; background: white; border-radius: 12px; padding: 15px; text-align: center;")
        self.today_lbl.setAlignment(Qt.AlignCenter)
        
        top_layout.addWidget(self.total_lbl)
        top_layout.addWidget(self.today_lbl)
        layout.addLayout(top_layout)
        layout.addSpacing(15)

        # 折线图
        self.plot_widget = pg.PlotWidget(background='w')
        self.plot_widget.setStyleSheet("border-radius: 12px;")
        self.plot_widget.showGrid(x=False, y=True, alpha=0.3)
        self.plot_widget.getAxis('bottom').setTicks([]) 
        layout.addWidget(self.plot_widget)

    def load_task_data(self):
        app_data = load_data()
        records = app_data.get("records", {})
        task_key = f"{self.goal}|{self.remark}"
        
        total_count = 0
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_count = 0
        daily_totals = {}

        # 专门过滤出这个 Task 的数据
        for date, tasks_dict in records.items():
            count = tasks_dict.get(task_key, 0)
            daily_totals[date] = count
            total_count += count
            if date == today_str:
                today_count = count

        self.total_lbl.setText(f"总计投递\n{total_count}")
        self.today_lbl.setText(f"今日投递\n{today_count}")

        # 如果没有数据，给个默认空点防报错
        if not daily_totals:
            daily_totals = {today_str: 0}

        sorted_dates = sorted(daily_totals.keys())
        recent_dates = sorted_dates[-7:]
        y_data = [daily_totals[d] for d in recent_dates]
        x_data = list(range(len(recent_dates)))

        pen = pg.mkPen(color=(94, 92, 230), width=3) # 单独任务用紫色区分
        self.plot_widget.plot(x_data, y_data, pen=pen, symbol='o', symbolSize=8, symbolBrush=(94, 92, 230))
        ticks = [list(zip(x_data, [d[-5:] for d in recent_dates]))]
        self.plot_widget.getAxis('bottom').setTicks(ticks)


# ==========================================
# 悬浮窗 (Mini Widget) 
# ==========================================
class MiniWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.goal = ""
        self.remark = ""
        self.today_str = ""
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(160, 160)
        self.setup_ui()
        self._is_tracking = False
        self._start_pos = QPoint()

    def setup_ui(self):
        self.card = QFrame(self)
        self.card.setStyleSheet("QFrame { background-color: rgba(255, 255, 255, 0.95); border-radius: 20px; }")
        self.card.setGeometry(10, 10, 140, 140)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.count_lbl = QLabel("0")
        self.count_lbl.setStyleSheet("font-family: -apple-system, sans-serif; font-size: 56px; font-weight: 800; color: #1D1D1F;")
        self.count_lbl.setAlignment(Qt.AlignCenter)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedHeight(40)
        self.close_btn.setStyleSheet("""
            QPushButton { background-color: #FF3B30; color: white; font-size: 18px; font-weight: bold; border-radius: 12px; border: none; } 
            QPushButton:hover { background-color: #E0332A; }
            QPushButton:pressed { background-color: #C92D25; }
        """)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.go_back)

        self.add_btn = QPushButton("+1")
        self.add_btn.setFixedHeight(40)
        self.add_btn.setStyleSheet("""
            QPushButton { background-color: #34C759; color: white; font-size: 20px; font-weight: bold; border-radius: 12px; border: none; } 
            QPushButton:hover { background-color: #2EB150; }
            QPushButton:pressed { background-color: #289945; }
        """)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.increment_count)

        btn_layout.addWidget(self.close_btn)
        btn_layout.addWidget(self.add_btn)

        layout.addWidget(self.count_lbl)
        layout.addLayout(btn_layout)

    def load_task(self, goal, remark):
        self.goal = goal
        self.remark = remark
        self.today_str = datetime.now().strftime('%Y-%m-%d')
        
        app_data = load_data()
        task_key = f"{goal}|{remark}"
        if self.today_str not in app_data["records"]:
            app_data["records"][self.today_str] = {}
            
        current_count = app_data["records"][self.today_str].get(task_key, 0)
        self.count_lbl.setText(str(current_count))
        self.card.setToolTip(f"目标: {goal}\n备注: {remark}")

    def increment_count(self):
        app_data = load_data()
        task_key = f"{self.goal}|{self.remark}"
        if self.today_str not in app_data["records"]:
            app_data["records"][self.today_str] = {}
            
        current_count = app_data["records"][self.today_str].get(task_key, 0)
        new_count = current_count + 1
        app_data["records"][self.today_str][task_key] = new_count
        save_data(app_data)
        self.count_lbl.setText(str(new_count))

    def go_back(self):
        self.hide()
        self.main_window.show()
        self.main_window.refresh_dashboard()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_tracking = True
            self._start_pos = event.globalPosition().toPoint() - self.pos()
    def mouseMoveEvent(self, event):
        if self._is_tracking: self.move(event.globalPosition().toPoint() - self._start_pos)
    def mouseReleaseEvent(self, event):
        self._is_tracking = False


# ==========================================
# 主窗口 
# ==========================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Resume Tracker")
        self.resize(760, 520) 
        
        self.setStyleSheet("""
            QWidget { font-family: -apple-system, sans-serif; background-color: #F5F5F7; color: #1D1D1F; }
            QLineEdit { padding: 12px 16px; background-color: #E8E8ED; border: none; border-radius: 10px; font-size: 14px; }
            QLineEdit:focus { background-color: #FFFFFF; border: 1px solid #007AFF; }
            QPushButton#PrimaryBtn { padding: 12px 20px; background-color: #007AFF; color: white; border: none; border-radius: 18px; font-size: 14px; font-weight: 600; }
            QPushButton#PrimaryBtn:hover { background-color: #0056b3; }
            QListWidget { border: none; background-color: transparent; outline: 0; }
            QListWidget::item { background: transparent; }
            QFrame#Card { background-color: #FFFFFF; border-radius: 14px; }
            
            QPushButton#IconBtn { background-color: #F5F5F7; color: #86868B; border-radius: 14px; font-size: 16px; font-weight: bold; border: none; margin-left: 5px; }
            QPushButton#IconBtn:hover { background-color: #E8E8ED; color: #1D1D1F; }
            /* 为不同功能按钮设定 Hover 颜色 */
            QPushButton#StatsBtn:hover { background-color: #5E5CE6; color: white; } /* 苹果紫 */
            QPushButton#CheckBtn:hover { background-color: #34C759; color: white; } /* 苹果绿 */
            QPushButton#DeleteBtn:hover { background-color: #FF3B30; color: white; } /* 苹果红 */
            
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #E8E8ED; color: #86868B; padding: 10px 25px; border-radius: 15px; margin-right: 10px; font-weight: bold; }
            QTabBar::tab:selected { background: #1D1D1F; color: white; }
        """)
        
        self.mini_widget = MiniWidget(self)
        self.setup_ui()
        self.load_saved_tasks()
        self.refresh_dashboard()

    def get_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 4)
        return shadow

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        self.tab_tasks = QWidget()
        self.setup_tasks_tab(self.tab_tasks)
        self.tab_dashboard = QWidget()
        self.setup_dashboard_tab(self.tab_dashboard)

        self.tabs.addTab(self.tab_tasks, "🚀 Tracker")
        self.tabs.addTab(self.tab_dashboard, "📊 Dashboard")
        main_layout.addWidget(self.tabs)

    def setup_tasks_tab(self, tab_widget):
        layout = QHBoxLayout(tab_widget)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(30)

        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)
        title_label = QLabel("New Target")
        title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText("Goal (e.g. Data Analyst)")
        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText("Remark (e.g. LinkedIn)")
        self.add_btn = QPushButton("Add to list")
        self.add_btn.setObjectName("PrimaryBtn")
        self.add_btn.clicked.connect(self.add_new_task_from_ui)

        left_layout.addWidget(title_label)
        left_layout.addSpacing(10)
        left_layout.addWidget(self.goal_input)
        left_layout.addWidget(self.remark_input)
        left_layout.addSpacing(10)
        left_layout.addWidget(self.add_btn)

        right_layout = QVBoxLayout()
        right_title = QLabel("Tasks")
        right_title.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.task_list = QListWidget()
        self.task_list.setSpacing(12)
        
        right_layout.addWidget(right_title)
        right_layout.addSpacing(10)
        right_layout.addWidget(self.task_list)

        layout.addLayout(left_layout, 4)
        layout.addLayout(right_layout, 6)

    def setup_dashboard_tab(self, tab_widget):
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(10, 20, 10, 10)
        
        top_layout = QHBoxLayout()
        self.total_lbl = QLabel("Total Apps\n0")
        self.total_lbl.setStyleSheet("font-size: 20px; font-weight: bold; background: white; border-radius: 15px; padding: 15px; text-align: center;")
        self.total_lbl.setAlignment(Qt.AlignCenter)
        
        self.today_lbl = QLabel("Today's Apps\n0")
        self.today_lbl.setStyleSheet("font-size: 20px; font-weight: bold; background: white; border-radius: 15px; padding: 15px; text-align: center;")
        self.today_lbl.setAlignment(Qt.AlignCenter)
        
        top_layout.addWidget(self.total_lbl)
        top_layout.addWidget(self.today_lbl)

        self.plot_widget = pg.PlotWidget(background='w')
        self.plot_widget.setStyleSheet("border-radius: 15px;")
        self.plot_widget.showGrid(x=False, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Total Applications')
        self.plot_widget.getAxis('bottom').setTicks([]) 

        layout.addLayout(top_layout)
        layout.addSpacing(20)
        layout.addWidget(self.plot_widget)

    def refresh_dashboard(self):
        app_data = load_data()
        records = app_data.get("records", {})
        
        total_count = 0
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_count = 0
        daily_totals = {}

        for date, tasks_dict in records.items():
            day_sum = sum(tasks_dict.values())
            daily_totals[date] = day_sum
            total_count += day_sum
            if date == today_str:
                today_count = day_sum

        self.total_lbl.setText(f"总投递量\n{total_count}")
        self.today_lbl.setText(f"今日投递\n{today_count}")

        if not daily_totals:
            daily_totals = {today_str: 0}

        sorted_dates = sorted(daily_totals.keys())
        recent_dates = sorted_dates[-7:]
        y_data = [daily_totals[d] for d in recent_dates]
        x_data = list(range(len(recent_dates)))

        self.plot_widget.clear()
        pen = pg.mkPen(color=(0, 122, 255), width=3) 
        self.plot_widget.plot(x_data, y_data, pen=pen, symbol='o', symbolSize=10, symbolBrush=(0, 122, 255))
        ticks = [list(zip(x_data, [d[-5:] for d in recent_dates]))]
        self.plot_widget.getAxis('bottom').setTicks(ticks)

    def load_saved_tasks(self):
        app_data = load_data()
        for task in app_data.get("tasks", []):
            self.render_task_item(task["goal"], task["remark"])

    def add_new_task_from_ui(self):
        goal = self.goal_input.text().strip()
        remark = self.remark_input.text().strip()
        if not goal or not remark: return
        app_data = load_data()
        if not any(t["goal"] == goal and t["remark"] == remark for t in app_data["tasks"]):
            app_data["tasks"].append({"goal": goal, "remark": remark})
            save_data(app_data)
            self.render_task_item(goal, remark)
        self.remark_input.clear()

    def render_task_item(self, goal, remark):
        item_card = QFrame()
        item_card.setObjectName("Card")
        item_card.setGraphicsEffect(self.get_shadow())
        item_card.setFixedHeight(64)
        item_layout = QHBoxLayout(item_card)
        item_layout.setContentsMargins(20, 10, 15, 10)
        
        text_layout = QVBoxLayout()
        text_layout.setAlignment(Qt.AlignVCenter)
        goal_lbl = QLabel(goal)
        goal_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #1D1D1F;")
        remark_lbl = QLabel(remark)
        remark_lbl.setStyleSheet("font-size: 12px; font-weight: 400; color: #86868B;")
        text_layout.addWidget(goal_lbl)
        text_layout.addWidget(remark_lbl)

        # 新增：独立看板按钮 (📊)
        stats_btn = QPushButton("📊")
        stats_btn.setObjectName("IconBtn")
        stats_btn.setProperty("id", "StatsBtn")
        stats_btn.setFixedSize(36, 36)
        stats_btn.setCursor(Qt.PointingHandCursor)
        stats_btn.setToolTip("查看该任务数据")

        check_btn = QPushButton("✓")
        check_btn.setObjectName("IconBtn")
        check_btn.setProperty("id", "CheckBtn")
        check_btn.setFixedSize(36, 36)
        check_btn.setCursor(Qt.PointingHandCursor)
        
        delete_btn = QPushButton("✕")
        delete_btn.setObjectName("IconBtn")
        delete_btn.setProperty("id", "DeleteBtn")
        delete_btn.setFixedSize(36, 36)
        delete_btn.setCursor(Qt.PointingHandCursor)

        item_layout.addLayout(text_layout)
        item_layout.addStretch()
        item_layout.addWidget(stats_btn) # 把统计按钮放在打勾前面
        item_layout.addWidget(check_btn)
        item_layout.addWidget(delete_btn)

        list_item = QListWidgetItem(self.task_list)
        list_item.setSizeHint(QSize(0, 70))
        self.task_list.addItem(list_item)
        self.task_list.setItemWidget(list_item, item_card)

        # 绑定事件
        delete_btn.clicked.connect(lambda: self.remove_task(list_item, goal, remark))
        check_btn.clicked.connect(lambda: self.trigger_mini_widget(goal, remark))
        stats_btn.clicked.connect(lambda: self.show_task_dashboard(goal, remark))

    def remove_task(self, list_item, goal, remark):
        self.task_list.takeItem(self.task_list.row(list_item))
        app_data = load_data()
        app_data["tasks"] = [t for t in app_data["tasks"] if not (t["goal"] == goal and t["remark"] == remark)]
        save_data(app_data)

    def trigger_mini_widget(self, goal, remark):
        self.hide()
        self.mini_widget.load_task(goal, remark)
        self.mini_widget.show()
        screen_geometry = self.screen().availableGeometry()
        self.mini_widget.move(screen_geometry.width() - 250, 50)
        
    def show_task_dashboard(self, goal, remark):
        # 实例化并显示独立看板弹窗
        dialog = TaskDashboardDialog(goal, remark, self)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())