# -*- coding: utf-8 -*-
"""
Main GUI window
Author: vokrob (Данил Борков)
Date: 18.07.2025
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time


from ytdlp_gui.core.settings_manager import SettingsManager
from ytdlp_gui.gui.components.url_input import URLInputFrame
from ytdlp_gui.gui.components.format_selector import FormatSelectorFrame
from ytdlp_gui.gui.components.output_selector import OutputSelectorFrame
from ytdlp_gui.gui.components.progress_display import ProgressDisplayFrame
from ytdlp_gui.gui.components.download_queue import DownloadQueueFrame
from ytdlp_gui.gui.components.simple_url_input import SimpleURLInputFrame
from ytdlp_gui.gui.components.video_preview import VideoPreviewFrame
from ytdlp_gui.gui.components.download_options import DownloadOptionsFrame

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class KWP2000GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Диагностика Январь(M1.5.4N)")
        self.root.geometry("500x500")

        # Переменные
        self.port_var = tk.StringVar(value="COM2")
        self.baudrate_var = tk.IntVar(value=10400)
        self.connected = False
        self.kwp = None

        # Создаем интерфейс
        self.create_connection_frame()
        self.create_services_frame()
        self.create_log_frame()

        # Запрещаем изменение размеров окна
        self.root.resizable(False, False)

    def create_connection_frame(self):
        """Панель подключения"""
        frame = ttk.LabelFrame(self.root, text="Подключение", padding=10)
        frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # Порт
        ttk.Label(frame, text="Порт:").grid(row=0, column=0, sticky="e")
        self.port_entry = ttk.Entry(
            frame, textvariable=self.port_var, width=10)
        self.port_entry.grid(row=0, column=1, sticky="w")

        # Скорость
        ttk.Label(frame, text="Скорость:").grid(row=0, column=2, sticky="e")
        self.baudrate_combo = ttk.Combobox(frame,
                                           textvariable=self.baudrate_var,
                                           values=[10400, 38400, 57600],
                                           width=8)
        self.baudrate_combo.grid(row=0, column=3, sticky="w")

        # Кнопки подключения
        self.connect_btn = ttk.Button(
            frame, text="Подключиться", command=self.connect)
        self.connect_btn.grid(row=0, column=4, padx=5)

        self.disconnect_btn = ttk.Button(
            frame, text="Отключиться",
            command=self.disconnect,
            state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=5, padx=5)

        # Статус
        self.status_label = ttk.Label(
            frame, text="Отключено", foreground="red")
        self.status_label.grid(row=1, column=0, columnspan=6, pady=(5, 0))

    def create_services_frame(self):
        """Панель сервисов"""
        frame = ttk.LabelFrame(self.root, text="Сервисы", padding=10)
        frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        # Вкладки
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка общей диагностики
        self.create_general_tab()

        # Вкладка чтения параметров
        self.create_read_data_tab()

        # Вкладка управления
        self.create_control_tab()

    def create_general_tab(self):
        """Вкладка общей диагностики"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Общая диагностика")

        # Кнопки
        ttk.Button(tab, text="Идентификация ЭБУ",
                   command=self.read_ident).pack(pady=5, fill=tk.X)
        ttk.Button(tab, text="Прочитать ошибки",
                   command=self.read_dtc).pack(pady=5, fill=tk.X)
        ttk.Button(tab, text="Стереть ошибки",
                   command=self.clear_dtc).pack(pady=5, fill=tk.X)
        ttk.Button(tab, text="Сброс ЭБУ", command=self.ecu_reset).pack(
            pady=5, fill=tk.X)

        # Поле для вывода результатов
        self.general_result = scrolledtext.ScrolledText(
            tab, height=10, state=tk.DISABLED)
        self.general_result.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    def create_read_data_tab(self):
        """Вкладка чтения параметров"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Параметры")

        # Выбор идентификатора
        ttk.Label(tab, text="Идентификатор:").pack(pady=(5, 0))

        self.data_id_combo = ttk.Combobox(tab, values=[
            ("01 - Комплектация", 0x01),
            ("02 - End Of Line", 0x02),
            ("03 - Factory Test", 0x03),
            ("A0 - Immobilizer", 0xA0),
            ("A1 - Body Serial", 0xA1),
            ("A2 - Engine Serial", 0xA2),
            ("A3 - Manufacture Date", 0xA3)
        ], state="readonly")
        self.data_id_combo.pack(pady=5, fill=tk.X)
        self.data_id_combo.current(0)

        # Кнопки
        ttk.Button(tab, text="Прочитать данные",
                   command=self.read_data).pack(pady=5, fill=tk.X)

        # Поле для вывода
        self.data_result = scrolledtext.ScrolledText(
            tab, height=10, state=tk.DISABLED)
        self.data_result.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    def create_control_tab(self):
        """Вкладка управления исполнительными механизмами"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Управление")

        # Выбор устройства
        ttk.Label(tab, text="Устройство:").pack(pady=(5, 0))

        self.control_combo = ttk.Combobox(tab, values=[
            ("Бензонасос (09)", 0x09),
            ("Вентилятор (0A)", 0x0A),
            ("Кондиционер (0B)", 0x0B),
            ("Лампа неисправности (0C)", 0x0C),
            ("Клапан адсорбера (0D)", 0x0D),
            ("Регулятор ХХ (41)", 0x41),
            ("Обороты ХХ (42)", 0x42)
        ], state="readonly")
        self.control_combo.pack(pady=5, fill=tk.X)
        self.control_combo.current(0)

        # Состояние
        ttk.Label(tab, text="Действие:").pack(pady=(5, 0))

        self.action_combo = ttk.Combobox(tab, values=[
            "Включить",
            "Выключить",
            "Отчет о состоянии",
            "Сбросить в默认ное"
        ], state="readonly")
        self.action_combo.pack(pady=5, fill=tk.X)
        self.action_combo.current(0)

        # Кнопка
        ttk.Button(tab, text="Выполнить", command=self.control_device).pack(
            pady=5, fill=tk.X)

        # Поле для вывода
        self.control_result = scrolledtext.ScrolledText(
            tab, height=10, state=tk.DISABLED)
        self.control_result.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    def create_log_frame(self):
        """Лог сообщений"""
        frame = ttk.LabelFrame(self.root, text="Лог", padding=10)
        frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        self.log_text = scrolledtext.ScrolledText(
            frame, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Настройка grid для растягивания лога
        self.root.rowconfigure(2, weight=1)
        self.root.columnconfigure(0, weight=1)

    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def clear_result(self, text_widget):
        """Очистка поля вывода"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        text_widget.config(state=tk.DISABLED)

    def append_result(self, text_widget, text):
        """Добавление текста в поле вывода"""
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, text + "\n")
        text_widget.config(state=tk.DISABLED)
        text_widget.see(tk.END)

    def connect(self):
        """Подключение к ЭБУ"""
        port = self.port_var.get()
        baudrate = self.baudrate_var.get()

        try:
            self.kwp = KWP2000(port, baudrate)
            response = self.kwp.connect()

            if response.get('type') == 'response':
                self.connected = True
                self.connect_btn.config(state=tk.DISABLED)
                self.disconnect_btn.config(state=tk.NORMAL)
                self.status_label.config(text="Подключено", foreground="green")
                self.log_message(
                    f"Успешное подключение к {port} на скорости {baudrate}")
            else:
                self.log_message(f"Ошибка подключения: {response}")
                messagebox.showerror(
                    "Ошибка", f"Не удалось подключиться: {response}")

        except SerialException as e:
            self.log_message(f"Ошибка COM-порта: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка COM-порта: {str(e)}")
        except Exception as e:
            self.log_message(f"Неизвестная ошибка: {str(e)}")
            messagebox.showerror("Ошибка", f"Неизвестная ошибка: {str(e)}")

    def disconnect(self):
        """Отключение от ЭБУ"""
        if self.kwp:
            try:
                self.kwp.stop_dignostic_session()
                self.kwp.stop_communication()
                self.kwp.close()
                self.connected = False
                self.connect_btn.config(state=tk.NORMAL)
                self.disconnect_btn.config(state=tk.DISABLED)
                self.status_label.config(text="Отключено", foreground="red")
                self.log_message("Отключено от ЭБУ")
            except Exception as e:
                self.log_message(f"Ошибка отключения: {str(e)}")

    def read_ident(self):
        """Чтение идентификации ЭБУ"""
        if not self.check_connection():
            return

        self.clear_result(self.general_result)
        self.append_result(self.general_result, "=== Идентификация ЭБУ ===")

        try:
            response = self.kwp.read_ecu_identification(0x80)
            if response.get('type') == 'response':
                ident_data = KWPUtils.parse_identification(response['data'])

                for key, value in ident_data.items():
                    self.append_result(self.general_result, f"{key}: {value}")
            else:
                self.append_result(self.general_result, f"Ошибка: {response}")

        except Exception as e:
            self.append_result(self.general_result, f"Ошибка: {str(e)}")

    def read_dtc(self):
        """Чтение кодов ошибок"""
        if not self.check_connection():
            return

        self.clear_result(self.general_result)
        self.append_result(self.general_result, "=== Коды неисправностей ===")

        try:
            response = self.kwp.read_dtc_by_status()
            if response.get('type') == 'response':
                dtcs = KWPUtils.parse_dtcs(response['data'])

                if dtcs:
                    for dtc in dtcs:
                        self.append_result(self.general_result,
                                           f"{dtc['code']}: {', '.join(dtc['status_flags'])}")
                else:
                    self.append_result(self.general_result,
                                       "Ошибки не обнаружены")
            else:
                self.append_result(self.general_result, f"Ошибка: {response}")

        except Exception as e:
            self.append_result(self.general_result, f"Ошибка: {str(e)}")

    def clear_dtc(self):
        """Стирание кодов ошибок"""
        if not self.check_connection():
            return

        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите стереть все коды ошибок?"):
            self.clear_result(self.general_result)
            self.append_result(self.general_result, "=== Стирание ошибок ===")

            try:
                response = self.kwp.clear_dtc(0x0000)
                if response.get('type') == 'response':
                    self.append_result(self.general_result,
                                       "Коды ошибок успешно стерты")
                else:
                    self.append_result(self.general_result,
                                       f"Ошибка: {response}")
            except Exception as e:
                self.append_result(self.general_result, f"Ошибка: {str(e)}")

    def ecu_reset(self):
        """Сброс ЭБУ"""
        if not self.check_connection():
            return

        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите выполнить сброс ЭБУ?"):
            self.clear_result(self.general_result)
            self.append_result(self.general_result, "=== Сброс ЭБУ ===")

            try:
                response = self.kwp.ecu_reset(0x01)
                if response.get('type') == 'response':
                    self.append_result(self.general_result,
                                       "ЭБУ успешно сброшен")
                    # После сброса нужно переподключиться
                    self.disconnect()
                    time.sleep(2)
                    self.connect()
                else:
                    self.append_result(self.general_result,
                                       f"Ошибка: {response}")
            except Exception as e:
                self.append_result(self.general_result, f"Ошибка: {str(e)}")

    def read_data(self):
        """Чтение данных по идентификатору"""
        if not self.check_connection():
            return

        selected = self.data_id_combo.current()
        data_id = self.data_id_combo.cget("values")[selected][1]

        self.clear_result(self.data_result)
        self.append_result(
            self.data_result, f"=== Чтение данных (ID: {data_id:02X}) ===")

        try:
            response = self.kwp.read_data_by_local_id(data_id)
            if response.get('type') == 'response':
                # Простой вывод hex-дампом
                hex_data = ' '.join(f"{b:02X}" for b in response['data'])
                self.append_result(self.data_result, f"Данные: {hex_data}")

                # Здесь можно добавить специфичный разбор для каждого ID
                if data_id == 0x01:  # RLI_ASS
                    params = KWPUtils.parse_ass_params(response['data'])
                    for key, value in params.items():
                        self.append_result(self.data_result, f"{key}: {value}")
            else:
                self.append_result(self.data_result, f"Ошибка: {response}")

        except Exception as e:
            self.append_result(self.data_result, f"Ошибка: {str(e)}")

    def control_device(self):
        """Управление исполнительным устройством"""
        if not self.check_connection():
            return

        # Получаем выбранные параметры
        selected_device = self.control_combo.current()
        device_id = self.control_combo.cget("values")[selected_device][1]

        selected_action = self.action_combo.current()
        action_map = {
            0: (0x06, 0x01),  # Включить (ECO, ON)
            1: (0x06, 0x00),  # Выключить (ECO, OFF)
            2: (0x01, None),   # Отчет (RCS)
            3: (0x04, None)    # Сброс (RTD)
        }
        action_param, action_data = action_map[selected_action]

        self.clear_result(self.control_result)
        self.append_result(self.control_result,
                           f"=== Управление устройством {device_id:02X} ===")

        try:
            if action_data is not None:
                response = self.kwp.input_output_control(
                    device_id, action_param, bytes([action_data]))
            else:
                response = self.kwp.input_output_control(
                    device_id, action_param)

            if response.get('type') == 'response':
                self.append_result(self.control_result,
                                   "Команда выполнена успешно")
                # Выводим ответные данные, если они есть
                if response['data']:
                    hex_data = ' '.join(f"{b:02X}" for b in response['data'])
                    self.append_result(self.control_result,
                                       f"Ответ: {hex_data}")
            else:
                self.append_result(self.control_result, f"Ошибка: {response}")

        except Exception as e:
            self.append_result(self.control_result, f"Ошибка: {str(e)}")

    def check_connection(self):
        """Проверка подключения"""
        if not self.connected:
            messagebox.showwarning("Ошибка", "Сначала подключитесь к ЭБУ")
            return False
        return True
