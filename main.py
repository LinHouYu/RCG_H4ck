import sys, threading, time, os
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QVBoxLayout, QGridLayout
from PyQt6.QtGui import QPixmap, QPalette, QBrush, QIcon
from PyQt6.QtCore import Qt
import pymem

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class GameEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RCG_H4ck - By LinHouYu")
        self.setFixedSize(480, 300)
        self.setWindowIcon(QIcon(resource_path("icon.ico")))

        bg_path = resource_path("background.png")
        if os.path.exists(bg_path):
            bg = QPixmap(bg_path)
            if not bg.isNull():
                palette = QPalette()
                palette.setBrush(QPalette.ColorRole.Window,
                                 QBrush(bg.scaled(self.size(),
                                                  Qt.AspectRatioMode.IgnoreAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)))
                self.setPalette(palette)

        self.pm = None
        self.module_coin = None
        self.module_hp = None
        self.freeze_coin_flag = False
        self.freeze_hp_flag = False

        self.coin_input = QLineEdit()
        self.coin_input.setPlaceholderText("比如：99999.99")
        self.coin_freeze = QCheckBox("冻结金币")
        self.coin_btn = QPushButton("应用金币修改")
        self.coin_btn.clicked.connect(self.set_coin)

        self.hp_input = QLineEdit()
        self.hp_input.setPlaceholderText("比如：220")
        self.hp_freeze = QCheckBox("冻结生命值")
        self.hp_btn = QPushButton("应用生命值修改")
        self.hp_btn.clicked.connect(self.set_hp)

        self.status_label = QLabel("● 未连接")
        self.status_label.setStyleSheet(
            "color: #B0B0B0; font-weight: 600; "
            "background-color: rgba(0,0,0,0.35); padding: 3px 8px; border-radius: 5px;"
        )

        grid = QGridLayout()
        grid.addWidget(QLabel("金币:"), 0, 0)
        grid.addWidget(self.coin_input, 0, 1)
        grid.addWidget(self.coin_freeze, 0, 2)
        grid.addWidget(self.coin_btn, 0, 3)

        grid.addWidget(QLabel("生命值:"), 1, 0)
        grid.addWidget(self.hp_input, 1, 1)
        grid.addWidget(self.hp_freeze, 1, 2)
        grid.addWidget(self.hp_btn, 1, 3)

        vbox = QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addStretch(1)
        vbox.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.setLayout(vbox)

        self.try_connect("RiverCityGirls.exe")

    def set_status(self, ok, text):
        color = "#D73A49" if ok else "#B0B0B0"
        self.status_label.setText(f"● {text}")
        self.status_label.setStyleSheet(
            f"color: {color}; font-weight: 600; "
            "background-color: rgba(0,0,0,0.35); padding: 3px 8px; border-radius: 5px;"
        )

    def try_connect(self, process_name):
        try:
            self.pm = pymem.Pymem(process_name)
            self.module_coin = pymem.process.module_from_name(self.pm.process_handle, "UnityPlayer.dll").lpBaseOfDll
            self.module_hp = pymem.process.module_from_name(self.pm.process_handle, "mono-2.0-bdwgc.dll").lpBaseOfDll
            self.set_status(True, f"已连接 {process_name}")
        except:
            self.pm = None
            self.set_status(False, "未连接（启动游戏后重试）")

    def resolve_coin_addr(self):
        base_offset = 0x01B1BC80
        offsets = [0x58, 0x0, 0x1D8, 0x0, 0x18, 0x38]
        final_offset = 0x8C
        addr = self.pm.read_longlong(self.module_coin + base_offset)
        for off in offsets:
            addr = self.pm.read_longlong(addr + off)
        return addr + final_offset

    def resolve_hp_addr(self):
        base_offset = 0x007521E0
        offsets = [0x290, 0x700, 0x98, 0x78, 0x158, 0x30]
        final_offset = 0x348
        addr = self.pm.read_longlong(self.module_hp + base_offset)
        for off in offsets:
            addr = self.pm.read_longlong(addr + off)
        return addr + final_offset

    def set_coin(self):
        if not self.pm:
            self.set_status(False, "未连接")
            return
        try:
            value = float(self.coin_input.text())
            addr = self.resolve_coin_addr()
            self.pm.write_float(addr, value)
            self.set_status(True, f"金币已改为 {value:g}")
            if self.coin_freeze.isChecked() and not self.freeze_coin_flag:
                self.freeze_coin_flag = True
                threading.Thread(target=self.freeze_coin, args=(value,), daemon=True).start()
            elif not self.coin_freeze.isChecked():
                self.freeze_coin_flag = False
        except:
            self.set_status(False, "金币写入失败")

    def set_hp(self):
        if not self.pm:
            self.set_status(False, "未连接")
            return
        try:
            value = int(self.hp_input.text())
            addr = self.resolve_hp_addr()
            self.pm.write_int(addr, value)
            self.set_status(True, f"生命值已改为 {value}")
            if self.hp_freeze.isChecked() and not self.freeze_hp_flag:
                self.freeze_hp_flag = True
                threading.Thread(target=self.freeze_hp, args=(value,), daemon=True).start()
            elif not self.hp_freeze.isChecked():
                self.freeze_hp_flag = False
        except:
            self.set_status(False, "生命值写入失败")

    def freeze_coin(self, value):
        while self.freeze_coin_flag:
            try:
                addr = self.resolve_coin_addr()
                self.pm.write_float(addr, value)
            except:
                self.freeze_coin_flag = False
                break
            time.sleep(0.1)

    def freeze_hp(self, value):
        while self.freeze_hp_flag:
            try:
                addr = self.resolve_hp_addr()
                self.pm.write_int(addr, value)
            except:
                self.freeze_hp_flag = False
                break
            time.sleep(0.1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameEditor()
    window.show()
    sys.exit(app.exec())
