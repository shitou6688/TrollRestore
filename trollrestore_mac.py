# 巨魔安装器 macOS 版 - 连接设备 → 点安装 → 弹卡密 → 安装 → 成功弹窗
import sys
import asyncio
import qasync
import threading
import traceback
from pathlib import Path
import uuid
import hashlib
import time
import os
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QDialog, QLineEdit, QMessageBox, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from packaging.version import parse as parse_version
import requests
import sys

def resource_path(relative_path):
    """获取资源文件绝对路径（兼容 PyInstaller 打包和源码运行）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)
from sparserestore import backup, perform_restore


# ========== 安装记录管理 ==========

def _get_app_dir():
    """macOS 数据目录"""
    base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'TrollRestore')
    os.makedirs(base, exist_ok=True)
    return base


def _get_records_path():
    """获取安装记录文件路径"""
    return os.path.join(_get_app_dir(), 'install_records.json')


def load_install_records():
    """读取安装记录"""
    path = _get_records_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'records': [], 'total_unique': 0, 'total_all': 0}


def save_install_records(data):
    """写入安装记录"""
    path = _get_records_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ========== 卡密验证对话框 ==========

class PasswordDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.kami = ''
        self.device_code = hashlib.md5(str(uuid.getnode()).encode()).hexdigest()
        self.initUI()


    def initUI(self):
        self.setWindowTitle('巨魔安装器')
        self.setFixedSize(480, 380)
        self.setStyleSheet('QDialog { background-color: #f0f4f8; }')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(
            "QFrame#card { background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; }"
        )
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(0)

        title = QLabel('巨魔安装器')
        title.setFont(QFont('', 18, QFont.Bold))
        title.setStyleSheet('color: #111827; margin-bottom: 12px; background: transparent; border: none;')
        card_layout.addWidget(title)

        self.label = QLabel('请输入卡密')
        self.label.setFont(QFont('', 11))
        self.label.setStyleSheet('color: #6b7280; margin-bottom: 6px; background: transparent; border: none;')
        card_layout.addWidget(self.label)

        self.password_input = QLineEdit()
        self.password_input.setFixedHeight(38)
        self.password_input.setFont(QFont('', 12))
        self.password_input.setPlaceholderText('在此粘贴卡密...')
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 0 14px;
                border: 1px solid #d1d5db; border-radius: 6px;
                background-color: #ffffff; color: #1f2937;
            }
            QLineEdit:focus { border-color: #6366f1; }
            QLineEdit::placeholder { color: #9ca3af; }
        """)
        self.password_input.returnPressed.connect(self.verify_password)
        card_layout.addWidget(self.password_input)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        spacer.setStyleSheet('background: transparent;')
        card_layout.addWidget(spacer)

        self.confirm_button = QPushButton('验  证')
        self.confirm_button.setCursor(Qt.PointingHandCursor)
        self.confirm_button.setFixedHeight(38)
        self.confirm_button.setFont(QFont('', 12, QFont.Bold))
        self.confirm_button.setStyleSheet("""
            QPushButton { background-color: #6366f1; color: white; border: none; border-radius: 6px; letter-spacing: 2px }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton:pressed { background-color: #4338ca; }
        """)
        self.confirm_button.clicked.connect(self.verify_password)
        card_layout.addWidget(self.confirm_button)

        wx_label = QLabel('获取卡密 V：jiesuo66688')
        wx_label.setAlignment(Qt.AlignCenter)
        wx_label.setFont(QFont('', 11, QFont.Medium))
        wx_label.setStyleSheet("""
            color: #166534;
            background-color: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            padding: 10px 16px;
            margin: 12px 0 0 0;
        """)
        card_layout.addWidget(wx_label)
        main_layout.addWidget(card)
        self.setLayout(main_layout)

    def verify_password(self):
        try:
            kami = self.password_input.text().strip()
            if not kami:
                QMessageBox.warning(self, '错误', '请输入卡密！')
                return False

            params = {
                'api': 'kmlogon',
                'app': '10003',
                'kami': kami,
                'markcode': self.device_code
            }

            try:
                response = requests.get(
                    'http://124.221.171.80/api.php',
                    params=params,
                    timeout=10,
                    headers={'User-Agent': 'TrollRestore/1.0'},
                    verify=False
                )
                response.raise_for_status()
                result = response.json()

                if result.get('code') == 200:
                    self.kami = kami
                    QMessageBox.information(self, '成功', '卡密验证成功！')
                    self.accept()
                    return True
                else:
                    error_msg = result.get('msg', '卡密验证失败！')
                    QMessageBox.warning(self, '错误', error_msg)
                    self.password_input.clear()
                    self.password_input.setFocus()
                    return False

            except requests.exceptions.Timeout:
                QMessageBox.critical(self, '错误', '服务器连接超时，请检查网络连接后重试！')
            except requests.exceptions.ConnectionError:
                QMessageBox.critical(self, '错误', '无法连接到服务器，请检查网络连接或稍后重试！')
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, '错误', f'网络请求失败：{str(e)}')
            except ValueError as e:
                QMessageBox.critical(self, '错误', f'服务器返回数据格式错误：{str(e)}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'验证失败：{str(e)}')

            self.password_input.clear()
            self.password_input.setFocus()
            return False

        except Exception as e:
            QMessageBox.critical(self, '错误', f'系统错误：{str(e)}')
            self.password_input.clear()
            self.password_input.setFocus()
            return False


# ========== 安装成功弹窗（模态，只能点关闭退出） ==========

class InstallSuccessDialog(QDialog):
    def __init__(self, app_name):
        super().__init__()
        self.app_name = app_name
        self.initUI()


    def initUI(self):
        self.setWindowTitle('安装完成')
        self.setFixedSize(420, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet('QDialog { background-color: #f0f4f8; }')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(0)

        card = QFrame()
        card.setStyleSheet("QFrame#succard { background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; }")
        card.setObjectName('succard')
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(12)

        icon_label = QLabel('✅')
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet('font-size: 48px; background: transparent; border: none;')
        cl.addWidget(icon_label)

        title = QLabel('安装成功！')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('', 18, QFont.Bold))
        title.setStyleSheet('color: #111827; background: transparent; border: none;')
        cl.addWidget(title)

        # App 英文名 → 中文名映射（与下拉框一致）
        app_name_map = {
            'Tips': '提示', 'Books': '图书', 'Home': '家庭', 'Stocks': '股市',
            'Maps': '地图', 'Music': '音乐', 'News': '新闻', 'Health': '健康',
            'Podcasts': '播客', 'Weather': '天气', 'Calculator': '计算器',
            'Compass': '指南针', 'Clock': '时钟', 'Contacts': '通讯录',
            'FaceTime': 'FaceTime', 'Files': '文件', 'Find My': '查找',
            'FindMy': '查找', 'GarageBand': '库乐队', 'iMovie': 'iMovie',
            'iTunes Store': 'iTunes Store', 'Keynote': 'Keynote',
            'Magnifier': '放大镜', 'Measure': '测距仪', 'Notes': '备忘录',
            'Numbers': 'Numbers', 'Pages': 'Pages', 'Photo Booth': 'Photo Booth',
            'Reminders': '提醒事项', 'Safari': 'Safari', 'Shortcuts': '快捷指令',
            'Translate': '翻译', 'TV': 'TV', 'Voice Memos': '语音备忘录',
            'Watch': 'Watch', 'Mail': '邮件', 'Camera': '相机',
            'Photos': '照片', 'Calendar': '日历', 'Wallet': '钱包',
            'Apple Store': 'Apple Store', 'Clips': '可立拍', 'Support': '支持',
            'iCloud': 'iCloud', 'Trailers': 'iTunes Trailers', 'TestFlight': 'TestFlight',
            'Feedback': '反馈', 'TipsNotifications': '提示通知',
            'MobileStore': 'iTunes Store', 'MobileSlideShow': '照片',
            'MobileMail': '邮件', 'MobileCal': '日历', 'MobileNotes': '备忘录',
            'MobileSMS': '信息', 'MobilePhone': '电话', 'Preferences': '设置',
            'FieldTest': 'Field Test', 'Setup': '设置', 'StoreKitUIService': 'StoreKit',
            'WebContentAnalysisUI': '网页分析', 'WebSheet': '网页表单',
            'Spotlight': '搜索', 'SoundScapes': '声景', 'People': '联系人',
        }
        app_display = self.app_name.replace('.app', '')
        app_cn = app_name_map.get(app_display, app_display)

        msg = QLabel(
            f'设备即将重启，重启后请打开「<span style="color:#ef4444;font-weight:bold">{app_cn}</span>」应用'
        )
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setFont(QFont('', 12))
        msg.setStyleSheet('color: #374151; background: transparent; border: none;')
        msg.setTextFormat(Qt.RichText)
        cl.addWidget(msg)

        layout.addWidget(card)

        layout.addSpacing(16)

        close_btn = QPushButton('关闭')
        close_btn.setFixedHeight(40)
        close_btn.setFont(QFont('', 13, QFont.Bold))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: #6366f1; color: white; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton:pressed { background-color: #4338ca; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

# ========== 主窗口 ==========

class TrollRestoreGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.kami = ''
        self.initUI()
        asyncio.ensure_future(self.check_device())


    def initUI(self):
        self.setWindowTitle('巨魔安装器')
        self.setFixedSize(600, 550)

        central_widget = QWidget()
        central_widget.setStyleSheet('QWidget#central { background-color: #f0f4f8; }')
        central_widget.setObjectName('central')
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(14)

        title_label = QLabel('巨魔安装器')
        title_label.setFont(QFont('', 16, QFont.Bold))
        title_label.setStyleSheet('color: #111827; background: transparent; border: none; padding: 4px 0;')
        layout.addWidget(title_label)

        # 安装统计栏
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        self.stats_label = QLabel('已安装：0 台')
        self.stats_label.setFont(QFont('', 10, QFont.Medium))
        self.stats_label.setStyleSheet(
            'color: #6b7280; background-color: #ffffff; border: 1px solid #e2e8f0; '
            'border-radius: 4px; padding: 4px 10px;'
        )

        self.record_btn = QPushButton('查看记录')
        self.record_btn.setFixedHeight(26)
        self.record_btn.setFont(QFont('', 9))
        self.record_btn.setCursor(Qt.PointingHandCursor)
        self.record_btn.setStyleSheet("""
            QPushButton { background-color: #ffffff; color: #6366f1; border: 1px solid #c7d2fe; border-radius: 4px; padding: 0 8px; }
            QPushButton:hover { background-color: #eef2ff; }
        """)
        self.record_btn.clicked.connect(self._show_install_records)

        stats_row.addWidget(self.stats_label)
        stats_row.addWidget(self.record_btn)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        self._update_stats_label()

        device_card = QFrame()
        device_card.setStyleSheet("QFrame { background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; }")
        device_layout = QVBoxLayout(device_card)
        device_layout.setContentsMargins(20, 16, 20, 16)
        device_layout.setSpacing(10)

        dg_label = QLabel('设备信息')
        dg_label.setFont(QFont('', 11))
        dg_label.setStyleSheet('color: #6b7280; background: transparent; border: none; margin-bottom: 6px;')
        device_layout.addWidget(dg_label)

        self.device_info = QLabel('正在检查设备...')
        self.device_info.setAlignment(Qt.AlignCenter)
        self.device_info.setWordWrap(True)
        self.device_info.setMinimumHeight(48)
        self.device_info.setFont(QFont('', 11, QFont.Bold))
        self.device_info.setStyleSheet(
            'color: #166534; padding: 16px; '
            'background-color: #f0fdf4; border-radius: 6px; border: 1px solid #bbf7d0;'
        )
        device_layout.addWidget(self.device_info)

        self.refresh_button = QPushButton('刷新设备')
        self.refresh_button.setFixedHeight(34)
        self.refresh_button.setFont(QFont('', 11))
        self.refresh_button.setStyleSheet("""
            QPushButton { background-color: #ffffff; color: #374151; border: 1px solid #d1d5db; border-radius: 6px; }
            QPushButton:hover { background-color: #f9fafb; border-color: #9ca3af; }
            QPushButton:pressed { background-color: #f3f4f6; }
        """)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(lambda: asyncio.ensure_future(self.check_device()))
        device_layout.addWidget(self.refresh_button, 0, Qt.AlignCenter)
        layout.addWidget(device_card)

        app_card = QFrame()
        app_card.setStyleSheet("QFrame { background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; }")
        app_layout = QVBoxLayout(app_card)
        app_layout.setContentsMargins(20, 16, 20, 16)
        app_layout.setSpacing(8)

        ag_label = QLabel('目标系统应用')
        ag_label.setFont(QFont('', 11))
        ag_label.setStyleSheet('color: #6b7280; background: transparent; border: none; margin-bottom: 6px;')
        app_layout.addWidget(ag_label)

        hint = QLabel('请选择一个可注入的系统应用')
        hint.setFont(QFont('', 10))
        hint.setStyleSheet('color: #94a3b8; margin-bottom: 6px; background: transparent; border: none;')
        app_layout.addWidget(hint)

        self.app_combo = QComboBox()
        self.app_combo.setFont(QFont('', 12))
        self.app_combo.setFixedHeight(38)
        self.app_combo.setStyleSheet("""
            QComboBox {
                padding: 0 14px; border: 1px solid #d1d5db; border-radius: 6px;
                background-color: #ffffff; color: #1f2937;
            }
            QComboBox:hover { border-color: #9ca3af; }
            QComboBox::drop-down {
                subcontrol-origin: padding; subcontrol-position: top right;
                width: 30px; border-left: 1px solid #e2e8f0;
            }
            QComboBox QAbstractItemView {
                font-family: ''; font-size: 12px;
                padding: 4px; border: 1px solid #d1d5db;
                selection-background-color: #eef2ff; selection-color: #4338ca;
            }
        """)
        self.app_combo.addItem('连接设备后自动加载...')
        self.app_combo.setEnabled(False)
        app_layout.addWidget(self.app_combo)

        layout.addWidget(app_card)

        self.install_button = QPushButton('开始安装')
        self.install_button.setFixedHeight(42)
        self.install_button.setFont(QFont('', 13, QFont.Bold))
        self.install_button.setStyleSheet("""
            QPushButton { background-color: #6366f1; color: white; border: none; border-radius: 8px; }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton:pressed { background-color: #4338ca; }
            QPushButton:disabled { background-color: #e2e8f0; color: #94a3b8; border: 1px solid #e2e8f0; }
        """)
        self.install_button.setCursor(Qt.PointingHandCursor)
        self.install_button.clicked.connect(lambda: asyncio.ensure_future(self.install_trollstore()))
        layout.addWidget(self.install_button)

        self.ad_label = QLabel('长期合作V：jiesuo66688')
        self.ad_label.setAlignment(Qt.AlignCenter)
        self.ad_label.setFont(QFont('', 10, QFont.Medium))
        self.ad_label.setStyleSheet('color: #166534; background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 6px;')
        layout.addWidget(self.ad_label)

        self.install_button.setEnabled(False)

    def _update_stats_label(self):
        """更新统计标签"""
        data = load_install_records()
        unique = data.get('total_unique', 0)
        total = data.get('total_all', 0)
        if total > unique:
            self.stats_label.setText(f'已安装：{unique} 台（共 {total} 次）')
        else:
            self.stats_label.setText(f'已安装：{unique} 台')

    def _save_install_record(self, udid, serial, model, ios_ver, app_name):
        """保存安装记录，返回是否重复"""
        data = load_install_records()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 检查 UDID 是否已存在
        existing_udids = [r.get('udid') for r in data['records']]
        is_repeat = udid in existing_udids

        record = {
            'udid': udid,
            'serial': serial,
            'model': model,
            'ios_version': ios_ver,
            'app_used': app_name,
            'timestamp': now,
            'is_repeat': is_repeat,
        }
        data['records'].append(record)
        data['total_all'] = data.get('total_all', 0) + 1

        if not is_repeat:
            data['total_unique'] = data.get('total_unique', 0) + 1

        save_install_records(data)
        self._update_stats_label()
        return is_repeat

    def _show_install_records(self):
        """显示安装记录对话框"""
        data = load_install_records()
        records = data.get('records', [])

        dialog = QDialog(self)
        dialog.setWindowTitle('安装记录')
        dialog.setFixedSize(780, 430)
        dialog.setStyleSheet('QDialog { background-color: #f0f4f8; }')

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel(f'共安装 {data.get("total_unique", 0)} 台设备（{data.get("total_all", 0)} 次）')
        header.setFont(QFont('', 13, QFont.Bold))
        header.setStyleSheet('color: #111827; background: transparent; border: none;')
        layout.addWidget(header)

        if not records:
            empty = QLabel('暂无安装记录')
            empty.setAlignment(Qt.AlignCenter)
            empty.setFont(QFont('', 12))
            empty.setStyleSheet('color: #94a3b8; padding: 40px; background: transparent; border: none;')
            layout.addWidget(empty)
        else:
            scroll = QFrame()
            scroll.setStyleSheet(
                'QFrame { background-color: #ffffff; border-radius: 6px; border: 1px solid #e2e8f0; padding: 0; }'
            )
            scroll_layout = QVBoxLayout(scroll)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(0)

            # 表头
            hdr = QLabel(
                '<table style="width:100%;font-size:13px;color:#6b7280;border-collapse:collapse;">'
                '<tr style="background:#f9fafb;">'
                '<td style="padding:10px 8px;width:17%;font-weight:bold;">机型</td>'
                '<td style="padding:10px 8px;width:7%;font-weight:bold;">版本</td>'
                '<td style="padding:10px 8px;width:12%;font-weight:bold;">注入App</td>'
                '<td style="padding:10px 8px;width:28%;font-weight:bold;">UDID</td>'
                '<td style="padding:10px 8px;width:15%;font-weight:bold;">时间</td>'
                '<td style="padding:10px 8px;width:9%;font-weight:bold;">状态</td>'
                '<td style="padding:10px 8px;width:12%;font-weight:bold;">操作</td>'
                '</tr></table>'
            )
            hdr.setStyleSheet('background: transparent; border: none;')
            scroll_layout.addWidget(hdr)

            # 记录行
            for i, r in enumerate(records):
                udid_full = r.get('udid', '')
                badge = ('<span style="color:#f59e0b;">重复</span>' if r.get('is_repeat')
                         else '<span style="color:#16a34a;">新设备</span>')
                row_html = (
                    '<table style="width:100%;font-size:13px;color:#374151;border-collapse:collapse;">'
                    '<tr style="border-top:1px solid #f3f4f6;">'
                    f'<td style="padding:9px 8px;width:17%;">{r.get("model","")}</td>'
                    f'<td style="padding:9px 8px;width:7%;">{r.get("ios_version","")}</td>'
                    f'<td style="padding:9px 8px;width:12%;">{r.get("app_used","")}</td>'
                    f'<td style="padding:9px 8px;width:28%;font-size:10px;white-space:normal;word-break:break-all;">{udid_full}</td>'
                    f'<td style="padding:9px 8px;width:15%;font-size:11px;">{r.get("timestamp","")}</td>'
                    f'<td style="padding:9px 8px;width:9%;">{badge}</td>'
                    f'<td style="padding:9px 8px;width:12%;">'
                    f'<a href="del:{i}" style="color:#ef4444;text-decoration:none;font-size:12px;">删除</a>'
                    f'</td>'
                    '</tr></table>'
                )
                row_label = QLabel(row_html)
                row_label.setStyleSheet('background: transparent; border: none;')
                row_label.linkActivated.connect(lambda url, d=dialog, idx=i: self._on_delete_record(idx, d))
                scroll_layout.addWidget(row_label)

            layout.addWidget(scroll)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        if records:
            clear_btn = QPushButton('清空全部记录')
            clear_btn.setFixedHeight(34)
            clear_btn.setFont(QFont('', 11))
            clear_btn.setCursor(Qt.PointingHandCursor)
            clear_btn.setStyleSheet("""
                QPushButton { background-color: #ffffff; color: #ef4444; border: 1px solid #fca5a5; border-radius: 6px; }
                QPushButton:hover { background-color: #fef2f2; }
            """)
            clear_btn.clicked.connect(lambda: self._on_clear_all_records(dialog))
            btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        close_btn = QPushButton('关闭')
        close_btn.setFixedHeight(34)
        close_btn.setFont(QFont('', 11, QFont.Bold))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: #6366f1; color: white; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec_()

    def _on_delete_record(self, index, dialog):
        """删除单条安装记录"""
        reply = QMessageBox.question(dialog, '确认删除', '确定要删除这条安装记录吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        data = load_install_records()
        if index < len(data['records']):
            data['records'].pop(index)
            data['total_all'] = max(0, data['total_all'] - 1)
            # 重新计算唯一设备数
            udids = set(r.get('udid') for r in data['records'])
            data['total_unique'] = len(udids)
            save_install_records(data)
            self._update_stats_label()

        dialog.accept()
        QTimer.singleShot(100, self._show_install_records)

    def _on_clear_all_records(self, dialog):
        """清空全部安装记录"""
        reply = QMessageBox.question(dialog, '确认清空', '确定要清空全部安装记录吗？此操作不可恢复！',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        save_install_records({'records': [], 'total_unique': 0, 'total_all': 0})
        self._update_stats_label()

        dialog.accept()
        QTimer.singleShot(100, self._show_install_records)

    async def check_device(self):
        try:
            await self._check_device_async()
        except Exception as e:
            self.device_info.setText(f"检查设备时出错：{str(e)}")

    async def _check_device_async(self):
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.exceptions import NoDeviceConnectedError
        try:
            self.service_provider = await create_using_usbmux()
            device_class = await self.service_provider.get_value(key="DeviceClass")
            product_type = await self.service_provider.get_value(key="ProductType")
            device_build = await self.service_provider.get_value(key="BuildVersion")
            device_version = parse_version(self.service_provider.product_version)

            os_names = {
                "iPhone": "iOS", "iPad": "iPadOS", "iPod": "iOS",
                "AppleTV": "tvOS", "Watch": "watchOS",
                "RealityDevice": "visionOS",
            }
            os_name = (os_names[device_class] + " ") if device_class in os_names else ""
            # ProductType → 具体机型名称映射（完整版，对齐 betahub.cn）
            _device_models = {
                # === iPhone ===
                "iPhone8,1": "iPhone 6s", "iPhone8,2": "iPhone 6s Plus",
                "iPhone8,4": "iPhone SE",
                "iPhone9,1": "iPhone 7", "iPhone9,2": "iPhone 7 Plus",
                "iPhone9,3": "iPhone 7", "iPhone9,4": "iPhone 7 Plus",
                "iPhone10,1": "iPhone 8", "iPhone10,2": "iPhone 8 Plus",
                "iPhone10,3": "iPhone X", "iPhone10,4": "iPhone 8",
                "iPhone10,5": "iPhone 8 Plus", "iPhone10,6": "iPhone X",
                "iPhone11,2": "iPhone XS", "iPhone11,4": "iPhone XS Max",
                "iPhone11,6": "iPhone XS Max", "iPhone11,8": "iPhone XR",
                "iPhone12,1": "iPhone 11", "iPhone12,3": "iPhone 11 Pro",
                "iPhone12,5": "iPhone 11 Pro Max", "iPhone12,8": "iPhone SE (第2代)",
                "iPhone13,1": "iPhone 12 mini", "iPhone13,2": "iPhone 12",
                "iPhone13,3": "iPhone 12 Pro", "iPhone13,4": "iPhone 12 Pro Max",
                "iPhone14,2": "iPhone 13 Pro", "iPhone14,3": "iPhone 13 Pro Max",
                "iPhone14,4": "iPhone 13 mini", "iPhone14,5": "iPhone 13",
                "iPhone14,6": "iPhone SE (第3代)", "iPhone14,7": "iPhone 14",
                "iPhone14,8": "iPhone 14 Plus", "iPhone15,2": "iPhone 14 Pro",
                "iPhone15,3": "iPhone 14 Pro Max", "iPhone15,4": "iPhone 15",
                "iPhone15,5": "iPhone 15 Plus", "iPhone16,1": "iPhone 15 Pro",
                "iPhone16,2": "iPhone 15 Pro Max",
                "iPhone17,1": "iPhone 16 Pro", "iPhone17,2": "iPhone 16 Pro Max",
                "iPhone17,3": "iPhone 16", "iPhone17,4": "iPhone 16 Plus",
                "iPhone17,5": "iPhone 16e",
                "iPhone18,1": "iPhone 17 Pro", "iPhone18,2": "iPhone 17 Pro Max",
                "iPhone18,3": "iPhone 17", "iPhone18,4": "iPhone 17 Air",
                # === iPad ===
                "iPad1,1": "iPad",
                "iPad2,1": "iPad 2", "iPad2,2": "iPad 2", "iPad2,3": "iPad 2",
                "iPad2,4": "iPad 2", "iPad2,5": "iPad mini",
                "iPad2,6": "iPad mini", "iPad2,7": "iPad mini",
                "iPad3,1": "iPad 3", "iPad3,2": "iPad 3", "iPad3,3": "iPad 3",
                "iPad3,4": "iPad 4", "iPad3,5": "iPad 4", "iPad3,6": "iPad 4",
                "iPad4,1": "iPad Air", "iPad4,2": "iPad Air", "iPad4,3": "iPad Air",
                "iPad4,4": "iPad mini 2", "iPad4,5": "iPad mini 2",
                "iPad4,6": "iPad mini 2", "iPad4,7": "iPad mini 3",
                "iPad4,8": "iPad mini 3", "iPad4,9": "iPad mini 3",
                "iPad5,1": "iPad mini 4", "iPad5,2": "iPad mini 4",
                "iPad5,3": "iPad Air 2", "iPad5,4": "iPad Air 2",
                "iPad6,3": "iPad Pro (9.7寸)", "iPad6,4": "iPad Pro (9.7寸)",
                "iPad6,7": "iPad Pro (12.9寸)", "iPad6,8": "iPad Pro (12.9寸)",
                "iPad6,11": "iPad (第5代)", "iPad6,12": "iPad (第5代)",
                "iPad7,1": "iPad Pro 12.9寸 (第2代)", "iPad7,2": "iPad Pro 12.9寸 (第2代)",
                "iPad7,3": "iPad Pro 10.5寸", "iPad7,4": "iPad Pro 10.5寸",
                "iPad7,5": "iPad (第6代)", "iPad7,6": "iPad (第6代)",
                "iPad7,11": "iPad (第7代)", "iPad7,12": "iPad (第7代)",
                "iPad8,1": "iPad Pro 11寸", "iPad8,2": "iPad Pro 11寸",
                "iPad8,3": "iPad Pro 11寸", "iPad8,4": "iPad Pro 11寸",
                "iPad8,5": "iPad Pro 12.9寸 (第3代)", "iPad8,6": "iPad Pro 12.9寸 (第3代)",
                "iPad8,7": "iPad Pro 12.9寸 (第3代)", "iPad8,8": "iPad Pro 12.9寸 (第3代)",
                "iPad8,9": "iPad Pro 11寸 (第2代)", "iPad8,10": "iPad Pro 11寸 (第2代)",
                "iPad8,11": "iPad Pro 12.9寸 (第4代)", "iPad8,12": "iPad Pro 12.9寸 (第4代)",
                "iPad11,1": "iPad mini (第5代)", "iPad11,2": "iPad mini (第5代)",
                "iPad11,3": "iPad Air (第3代)", "iPad11,4": "iPad Air (第3代)",
                "iPad11,6": "iPad (第8代)", "iPad11,7": "iPad (第8代)",
                "iPad12,1": "iPad (第9代)", "iPad12,2": "iPad (第9代)",
                "iPad13,1": "iPad Air (第4代)", "iPad13,2": "iPad Air (第4代)",
                "iPad13,4": "iPad Pro 11寸 (第3代)", "iPad13,5": "iPad Pro 11寸 (第3代)",
                "iPad13,6": "iPad Pro 11寸 (第3代)", "iPad13,7": "iPad Pro 11寸 (第3代)",
                "iPad13,8": "iPad Pro 12.9寸 (第5代)", "iPad13,9": "iPad Pro 12.9寸 (第5代)",
                "iPad13,10": "iPad Pro 12.9寸 (第5代)", "iPad13,11": "iPad Pro 12.9寸 (第5代)",
                "iPad13,16": "iPad Air (第5代)", "iPad13,17": "iPad Air (第5代)",
                "iPad13,18": "iPad (第10代)", "iPad13,19": "iPad (第10代)",
                "iPad14,1": "iPad mini (第6代)", "iPad14,2": "iPad mini (第6代)",
                "iPad14,3": "iPad Pro 11寸 (第4代)", "iPad14,4": "iPad Pro 11寸 (第4代)",
                "iPad14,5": "iPad Pro 12.9寸 (第6代)", "iPad14,6": "iPad Pro 12.9寸 (第6代)",
                "iPad14,8": "iPad Air 11寸 (M2)", "iPad14,9": "iPad Air 11寸 (M2)",
                "iPad14,10": "iPad Air 13寸 (M2)", "iPad14,11": "iPad Air 13寸 (M2)",
                "iPad15,3": "iPad Air 11寸 (M3)", "iPad15,4": "iPad Air 11寸 (M3)",
                "iPad15,5": "iPad Air 13寸 (M3)", "iPad15,6": "iPad Air 13寸 (M3)",
                "iPad15,7": "iPad (第11代)", "iPad15,8": "iPad (第11代)",
                "iPad16,1": "iPad mini (第7代)", "iPad16,2": "iPad mini (第7代)",
                "iPad16,3": "iPad Pro 11寸 (第5代)", "iPad16,4": "iPad Pro 11寸 (第5代)",
                "iPad16,5": "iPad Pro 12.9寸 (第7代)", "iPad16,6": "iPad Pro 12.9寸 (第7代)",
                # === iPod touch ===
                "iPod7,1": "iPod touch (第6代)",
                "iPod9,1": "iPod touch (第7代)",
            }
            device_model = _device_models.get((product_type or '').strip(), product_type or device_class)
            # 获取 UDID
            device_udid = await self.service_provider.get_value(key="UniqueDeviceID") or ""


            if (
                device_version < parse_version("14.0")
                or device_version > parse_version("17.0")
                or parse_version("16.7") < device_version < parse_version("17.0")
                or device_version == parse_version("16.7")
                and device_build != "20H18"
            ):
                self.device_info.setText(f"{os_name}{device_version} ({device_build})\n\u4e0d\u652f\u6301\u7684\u7cfb\u7edf\u7248\u672c")
                if hasattr(self, '_auto_refresh_timer') and self._auto_refresh_timer.isActive():
                    self._auto_refresh_timer.stop()
                return

            self.device_info.setText(
                f"设备型号：{device_model}  系统版本：{device_version} ({device_build})\n"
                f"UDID：{device_udid}"
            )

            self.install_button.setEnabled(True)
            asyncio.ensure_future(self._load_system_apps())

            if hasattr(self, '_auto_refresh_timer') and self._auto_refresh_timer.isActive():
                self._auto_refresh_timer.stop()

        except NoDeviceConnectedError:
            self.device_info.setText("未连接设备\n请连接设备后等待自动识别...")

            if not hasattr(self, '_auto_refresh_timer'):
                self._auto_refresh_timer = QTimer()
                self._auto_refresh_timer.timeout.connect(lambda: asyncio.ensure_future(self.check_device()))
                self._auto_refresh_timer.start(1500)
            elif not self._auto_refresh_timer.isActive():
                self._auto_refresh_timer.start(1500)

        except Exception as e:
            # 连接错误也启动自动重连（设备重启、SSL断开等）
            self.device_info.setText(f"设备未就绪，正在自动重连...\n({str(e)[:60]})")

            if not hasattr(self, '_auto_refresh_timer'):
                self._auto_refresh_timer = QTimer()
                self._auto_refresh_timer.timeout.connect(lambda: asyncio.ensure_future(self.check_device()))
                self._auto_refresh_timer.start(1500)
            elif not self._auto_refresh_timer.isActive():
                self._auto_refresh_timer.start(1500)

    async def install_trollstore(self):
        selected_data = self.app_combo.currentData()
        if not selected_data:
            self.device_info.setText("请选择一个系统应用")
            return
        selected_app = selected_data

        if not hasattr(self, 'service_provider'):
            self.device_info.setText("设备未连接，请先连接设备")
            return

        # 点安装 → 弹卡密验证
        if not self.kami:
            password_dialog = PasswordDialog()
            if password_dialog.exec_() == QDialog.Accepted:
                self.kami = getattr(password_dialog, 'kami', '')
            else:
                return

        self.install_button.setEnabled(False)
        self.install_button.setText("安装中...")

        try:
            await self._install_trollstore_async(selected_app)
        except Exception as e:
            error_detail = traceback.format_exc()
            self.device_info.setText(f"安装出错：{str(e)}")
            try:
                with open(os.path.join(_get_app_dir(), "trollrestore_error.log"), "w", encoding="utf-8") as log:
                    log.write(error_detail)
            except:
                pass
        finally:
            self.install_button.setEnabled(True)
            self.install_button.setText("开始安装")

    async def _install_trollstore_async(self, selected_app):
        from pymobiledevice3.services.installation_proxy import InstallationProxyService
        from pymobiledevice3.services.diagnostics import DiagnosticsService
        from pymobiledevice3.exceptions import PyMobileDevice3Exception
        try:
            async with InstallationProxyService(self.service_provider) as ips:
                apps_json = await ips.get_apps(application_type="System", calculate_sizes=False)

            app_path = None
            if isinstance(apps_json, dict):
                for key, value in apps_json.items():
                    if isinstance(value, dict) and "Path" in value:
                        potential_path = Path(value["Path"])
                        if potential_path.name.lower() == selected_app.lower():
                            app_path = potential_path
                            selected_app = app_path.name
            elif isinstance(apps_json, list):
                for app in apps_json:
                    if isinstance(app, dict) and "Path" in app:
                        potential_path = Path(app["Path"])
                        if potential_path.name.lower() == selected_app.lower():
                            app_path = potential_path
                            selected_app = app_path.name

            if not app_path:
                self.device_info.setText(f"未找到系统应用 '{selected_app}'请确保该应用已安装在设备上")

                return
            elif Path("/private/var/containers/Bundle/Application") not in app_path.parents:
                self.device_info.setText(f"'{selected_app}' 不是可移除的系统应用")
                return

            app_uuid = app_path.parent.name

            if self.kami:
                try:
                    dev_serial = await self.service_provider.get_value(key='SerialNumber')
                    dev_udid = await self.service_provider.get_value(key='UniqueDeviceID')
                    dev_model = await self.service_provider.get_value(key='ProductType')
                    dev_ios = self.service_provider.product_version
                    params_ts = {
                        'api': 'ts_register',
                        'serial': dev_serial or '',
                        'markcode': '',
                        'udid': dev_udid or '',
                        'kami': self.kami,
                        'model': dev_model or '',
                        'ios': dev_ios or '',
                    }
                    try:
                        requests.get('http://124.221.171.80/trollstore-device-api.php',
                            params=params_ts, timeout=10,
                            headers={'User-Agent': 'TrollRestore/1.0'}, verify=False)
                    except:
                        pass
                except Exception:
                    pass

            # 从内嵌资源读取 PersistenceHelper（无需网络下载）
            try:
                helper_path = resource_path('PersistenceHelper_Embedded')
                with open(helper_path, 'rb') as hf:
                    helper_contents = hf.read()
                if len(helper_contents) < 1000:
                    raise Exception(f'内嵌文件异常：仅 {len(helper_contents)} 字节')
            except Exception as e:
                self.device_info.setText(f"读取内嵌 TrollStore Helper 失败：{e}")
                return

            self.device_info.setText(f"正在替换 {selected_app} 为 TrollStore Helper...")

            # 收集设备信息用于备份兼容性（在当前方法内重新获取，避免作用域问题）
            _dv = parse_version(self.service_provider.product_version)
            _db = await self.service_provider.get_value(key="BuildVersion")
            _dc = await self.service_provider.get_value(key="DeviceClass")
            device_info = {
                "ProductVersion": str(_dv),
                "BuildVersion": _db,
                "ProductType": await self.service_provider.get_value(key="ProductType") or "iPhone10,1",
                "DeviceClass": _dc or "iPhone",
                "SerialNumber": await self.service_provider.get_value(key="SerialNumber") or "",
                "UniqueDeviceID": await self.service_provider.get_value(key="UniqueDeviceID") or "",
            }
            back = backup.Backup(
                files=[
                    backup.Directory("", "RootDomain"),
                    backup.Directory("Library", "RootDomain"),
                    backup.Directory("Library/Preferences", "RootDomain"),
                    backup.ConcreteFile("Library/Preferences/temp", "RootDomain", owner=33, group=33, contents=helper_contents, inode=0),
                    backup.ConcreteFile("Library/Caches/jumo_kami.txt", "RootDomain", owner=501, group=501, contents=self.kami.encode('utf-8') if self.kami else b''),
                    backup.Directory(
                        "",
                        f"SysContainerDomain-../../../../../../../../var/backup/var/containers/Bundle/Application/{app_uuid}/{selected_app}",
                        owner=33,
                        group=33,
                    ),
                    backup.ConcreteFile(
                        "",
                        f"SysContainerDomain-../../../../../../../../var/backup/var/containers/Bundle/Application/{app_uuid}/{selected_app}/{selected_app.replace('.app','')}",
                        owner=33,
                        group=33,
                        contents=b"",
                        inode=0,
                    ),
                    backup.ConcreteFile(
                        "",
                        "SysContainerDomain-../../../../../../../../var/.backup.i/var/root/Library/Preferences/temp",
                        owner=501,
                        group=501,
                        contents=b"",
                    ),
                    backup.ConcreteFile("", "SysContainerDomain-../../../../../../../../crash_on_purpose", contents=b""),
                ],
                device_info=device_info
            )

            try:
                    self.device_info.setText("正在注入，请稍候...")
                    QApplication.processEvents()
                    try:
                        await perform_restore(back, reboot=False, lockdown_client=self.service_provider)
                    except Exception as restore_err:
                        import traceback
                        with open(os.path.join(_get_app_dir(), "trollrestore_error.log"), "w", encoding="utf-8") as err_log:
                            err_log.write(f"TrollRestore 错误日志\n")
                            err_log.write(f"设备: {self.service_provider.product_version}\n")
                            err_log.write(f"错误类型: {type(restore_err).__name__}\n")
                            err_log.write(f"错误信息: {str(restore_err)}\n")
                            err_log.write(f"\n完整堆栈:\n")
                            err_log.write(traceback.format_exc())
                        raise
            except PyMobileDevice3Exception as e:
                if "Find My" in str(e):
                    self.device_info.setText("请先关闭查找我的iPhone功能设置 -> [你的名字] -> 查找")

                    return
                elif "crash_on_purpose" not in str(e):
                    raise e

            # 先缓存设备信息（重启后连接断开，不能再调 get_value）
            _dev_udid = device_info.get('UniqueDeviceID', '')
            _dev_serial = device_info.get('SerialNumber', '')
            _dev_model = device_info.get('ProductType', '')
            _dev_ios = str(device_info.get('ProductVersion', ''))

            async with DiagnosticsService(self.service_provider) as diagnostics_service:
                self.device_info.setText("注入完成，正在重启设备...")
                QApplication.processEvents()
                await diagnostics_service.restart()

            # 记录安装（重启之后、弹窗之前）
            try:
                app_display = selected_app.replace('.app', '')
                is_repeat = self._save_install_record(_dev_udid, _dev_serial, _dev_model, _dev_ios, app_display)
            except Exception:
                pass  # 记录失败不影响主流程

            # 安装成功 → 弹模态对话框
            self.device_info.setText(f"安装完成！")
            self.install_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.app_combo.setEnabled(False)

            dialog = InstallSuccessDialog(selected_app)
            dialog.exec_()  # 模态

            # 点关闭 → 回到首页，清除卡密，重新检测设备
            self.kami = ''
            self.install_button.setEnabled(True)
            self.refresh_button.setEnabled(True)
            self.app_combo.clear()
            self.app_combo.addItem('连接设备后自动加载...')
            self.app_combo.setEnabled(False)
            self.device_info.setText('正在重新检测设备...')
            asyncio.ensure_future(self.check_device())

        except Exception as e:
            self.device_info.setText(f"安装过程出错：{str(e)}")

    async def _load_system_apps(self):
        name_map = {
            'Tips': '提示', 'Books': '图书', 'Home': '家庭', 'Stocks': '股市',
            'Maps': '地图', 'Music': '音乐', 'News': '新闻', 'Health': '健康',
            'Podcasts': '播客', 'Weather': '天气', 'Calculator': '计算器',
            'Compass': '指南针', 'Clock': '时钟', 'Contacts': '通讯录',
            'FaceTime': 'FaceTime', 'Files': '文件', 'Find My': '查找',
            'FindMy': '查找', 'GarageBand': '库乐队', 'iMovie': 'iMovie',
            'iTunes Store': 'iTunes Store', 'Keynote': 'Keynote',
            'Magnifier': '放大镜', 'Measure': '测距仪', 'Notes': '备忘录',
            'Numbers': 'Numbers', 'Pages': 'Pages', 'Photo Booth': 'Photo Booth',
            'Reminders': '提醒事项', 'Safari': 'Safari', 'Shortcuts': '快捷指令',
            'Translate': '翻译', 'TV': 'TV', 'Voice Memos': '语音备忘录',
            'Watch': 'Watch', 'Mail': '邮件', 'Camera': '相机',
            'Photos': '照片', 'Calendar': '日历', 'Wallet': '钱包',
            'Apple Store': 'Apple Store', 'Clips': '可立拍', 'Support': '支持',
            'iCloud': 'iCloud', 'Trailers': 'iTunes Trailers', 'TestFlight': 'TestFlight',
            'Feedback': '反馈', 'TipsNotifications': '提示通知',
            'MobileStore': 'iTunes Store', 'MobileSlideShow': '照片',
            'MobileMail': '邮件', 'MobileCal': '日历', 'MobileNotes': '备忘录',
            'MobileSMS': '信息', 'MobilePhone': '电话', 'Preferences': '设置',
            'FieldTest': 'Field Test', 'Setup': '设置', 'StoreKitUIService': 'StoreKit',
            'WebContentAnalysisUI': '网页分析', 'WebSheet': '网页表单',
            'Spotlight': '搜索', 'SoundScapes': '声景', 'People': '联系人',
        }
        priority_order = ['Tips', 'Books', 'Home', 'Stocks']

        try:
            from pymobiledevice3.services.installation_proxy import InstallationProxyService
            async with InstallationProxyService(self.service_provider) as ips:
                apps_json = await ips.get_apps(application_type="System", calculate_sizes=False)

            self.app_combo.clear()
            removable_apps = []

            if isinstance(apps_json, dict):
                for key, value in apps_json.items():
                    if isinstance(value, dict) and "Path" in value:
                        app_path = Path(value["Path"])
                        if Path("/private/var/containers/Bundle/Application") in app_path.parents:
                            eng_name = app_path.name.replace('.app', '')
                            cn_name = name_map.get(eng_name) or name_map.get(eng_name.lower()) or name_map.get(eng_name.replace(' ','')) or eng_name
                            removable_apps.append((cn_name, eng_name, app_path.name))
            elif isinstance(apps_json, list):
                for app in apps_json:
                    if isinstance(app, dict) and "Path" in app:
                        app_path = Path(app["Path"])
                        if Path("/private/var/containers/Bundle/Application") in app_path.parents:
                            eng_name = app_path.name.replace('.app', '')
                            cn_name = name_map.get(eng_name) or name_map.get(eng_name.lower()) or name_map.get(eng_name.replace(' ','')) or eng_name
                            removable_apps.append((cn_name, eng_name, app_path.name))

            def sort_key(item):
                cn_name, eng_name, _ = item
                if eng_name in priority_order:
                    return (0, priority_order.index(eng_name))
                return (1, cn_name.lower())
            removable_apps.sort(key=sort_key)

            if removable_apps:
                for cn_name, eng_name, app_filename in removable_apps:
                    self.app_combo.addItem(cn_name, app_filename)
                self.app_combo.setEnabled(True)
                self.app_combo.setCurrentIndex(0)
            else:
                self.app_combo.addItem('未找到可注入应用')
        except Exception:
            self.app_combo.clear()
            self.app_combo.addItem('加载失败，请刷新')

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    font = QFont('', 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    gui = TrollRestoreGUI()
    gui.show()
    with loop:
        loop.run_forever()

if __name__ == '__main__':
    main()
