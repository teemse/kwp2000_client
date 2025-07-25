import customtkinter as ctk
from tkinter import scrolledtext, messagebox
from core.kwp2000 import KWP2000, KWPUtils
from serial import SerialException
import time


class KWP2000GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Диагностика Январь(M1.5.4N)")
        self.root.geometry("500x500")

        # Настройка темы
        ctk.set_appearance_mode("System")  # Системная тема
        ctk.set_default_color_theme("blue")  # Синяя цветовая тема

        # Переменные
        self.port_var = ctk.StringVar(value="COM2")
        self.baudrate_var = ctk.IntVar(value=10400)
        self.connected = False
        self.kwp = None

        # Создаем интерфейс
        self.create_connection_frame()
        self.create_services_frame()
        self.create_log_frame()

        # Запрещаем изменение размеров окна
        # self.root.resizable(False, False)

    def create_connection_frame(self):
        """Панель подключения"""
        frame = ctk.CTkFrame(self.root, corner_radius=10)
        frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew", columnspan=2)

        # Заголовок
        ctk.CTkLabel(frame,
                     text="Подключение",
                     font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=6, pady=(0, 10))

        # Порт
        ctk.CTkLabel(frame, text="Порт:").grid(
            row=1, column=0, sticky="e", padx=(10, 0))
        self.port_entry = ctk.CTkEntry(
            frame, textvariable=self.port_var, width=100)
        self.port_entry.grid(row=1, column=1, sticky="w")

        # Скорость
        ctk.CTkLabel(frame, text="Скорость:").grid(
            row=1, column=2, sticky="e", padx=(10, 0))
        self.baudrate_combo = ctk.CTkComboBox(frame,
                                              variable=self.baudrate_var,
                                              values=[
                                                  "10400", "38400", "57600"],
                                              width=100)
        self.baudrate_combo.grid(row=1, column=3, sticky="w")

        # Кнопки подключения
        self.connect_btn = ctk.CTkButton(
            frame,
            text="Подключиться",
            command=self.connect,
            fg_color="green",
            hover_color="dark green")
        self.connect_btn.grid(row=1, column=4, padx=10)

        self.disconnect_btn = ctk.CTkButton(
            frame, text="Отключиться",
            command=self.disconnect,
            state="disabled",
            fg_color="red", hover_color="dark red")
        self.disconnect_btn.grid(row=1, column=5, padx=(0, 10))

        # Статус
        self.status_label = ctk.CTkLabel(
            frame, text="Отключено", text_color="red")
        self.status_label.grid(row=2, column=0, columnspan=6, pady=(5, 10))

    def create_services_frame(self):
        """Панель сервисов"""
        frame = ctk.CTkFrame(self.root, corner_radius=10)
        frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew", rowspan=2)

        # Заголовок
        ctk.CTkLabel(frame, text="Сервисы", font=(
            "Arial", 14, "bold")).pack(pady=(5, 10))

        # Вкладки
        self.notebook = ctk.CTkTabview(frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Вкладка общей диагностики
        self.create_general_tab()

        # Вкладка чтения параметров
        self.create_read_data_tab()

        # Вкладка управления
        self.create_control_tab()

    def create_general_tab(self):
        """Вкладка общей диагностики"""
        tab = self.notebook.add("Общая диагностика")

        # Кнопки
        ctk.CTkButton(tab, text="Идентификация ЭБУ",
                      command=self.read_ident).pack(pady=5, fill="x", padx=10)
        ctk.CTkButton(tab, text="Прочитать ошибки",
                      command=self.read_dtc).pack(pady=5, fill="x", padx=10)
        ctk.CTkButton(tab, text="Стереть ошибки",
                      command=self.clear_dtc).pack(pady=5, fill="x", padx=10)
        ctk.CTkButton(tab, text="Сброс ЭБУ", command=self.ecu_reset).pack(
            pady=5, fill="x", padx=10)

        # Поле для вывода результатов
        self.general_result = scrolledtext.ScrolledText(
            tab, height=10, state="disabled", wrap="word")
        self.general_result.pack(
            fill="both", expand=True, pady=(5, 10), padx=10)

    def create_read_data_tab(self):
        """Вкладка чтения параметров"""
        tab = self.notebook.add("Параметры")

        # Выбор идентификатора
        ctk.CTkLabel(tab, text="Идентификатор:").pack(
            pady=(5, 0), padx=10, anchor="w")

        self.data_id_combo = ctk.CTkComboBox(tab, values=[
            "01 - Комплектация (0x01)",
            "02 - End Of Line (0x02)",
            "03 - Factory Test (0x03)",
            "A0 - Immobilizer (0xA0)",
            "A1 - Body Serial (0xA1)",
            "A2 - Engine Serial (0xA2)",
            "A3 - Manufacture Date (0xA3)"
        ], state="readonly")
        self.data_id_combo.pack(pady=5, fill="x", padx=10)
        self.data_id_combo.set("01 - Комплектация (0x01)")

        # Кнопки
        ctk.CTkButton(tab, text="Прочитать данные",
                      command=self.read_data).pack(pady=5, fill="x", padx=10)

        # Поле для вывода
        self.data_result = scrolledtext.ScrolledText(
            tab, height=10, state="disabled", wrap="word")
        self.data_result.pack(fill="both", expand=True, pady=(5, 10), padx=10)

    def create_control_tab(self):
        """Вкладка управления исполнительными механизмами"""
        tab = self.notebook.add("Управление")

        # Выбор устройства
        ctk.CTkLabel(tab, text="Устройство:").pack(
            pady=(5, 0), padx=10, anchor="w")

        self.control_combo = ctk.CTkComboBox(tab, values=[
            "Бензонасос (0x09)",
            "Вентилятор (0x0A)",
            "Кондиционер (0x0B)",
            "Лампа неисправности (0x0C)",
            "Клапан адсорбера (0x0D)",
            "Регулятор ХХ (0x41)",
            "Обороты ХХ (0x42)"
        ], state="readonly")
        self.control_combo.pack(pady=5, fill="x", padx=10)
        self.control_combo.set("Бензонасос (0x09)")

        # Состояние
        ctk.CTkLabel(tab, text="Действие:").pack(
            pady=(5, 0), padx=10, anchor="w")

        self.action_combo = ctk.CTkComboBox(tab, values=[
            "Включить",
            "Выключить",
            "Отчет о состоянии",
            "Сбросить в默认ное"
        ], state="readonly")
        self.action_combo.pack(pady=5, fill="x", padx=10)
        self.action_combo.set("Включить")

        # Кнопка
        ctk.CTkButton(tab, text="Выполнить", command=self.control_device).pack(
            pady=5, fill="x", padx=10)

        # Поле для вывода
        self.control_result = scrolledtext.ScrolledText(
            tab, height=10, state="disabled", wrap="word")
        self.control_result.pack(
            fill="both", expand=True, pady=(5, 10), padx=10)

    def create_log_frame(self):
        """Лог сообщений"""
        frame = ctk.CTkFrame(self.root, corner_radius=10)
        frame.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

        # Заголовок
        ctk.CTkLabel(frame, text="Лог сообщений", font=(
            "Arial", 14, "bold")).pack(pady=(5, 10))

        self.log_text = scrolledtext.ScrolledText(
            frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Настройка grid для растягивания лога
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(1, weight=1)

    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.config(state="disabled")
        self.log_text.see("end")

    def clear_result(self, text_widget):
        """Очистка поля вывода"""
        text_widget.config(state="normal")
        text_widget.delete(1.0, "end")
        text_widget.config(state="disabled")

    def append_result(self, text_widget, text):
        """Добавление текста в поле вывода"""
        text_widget.config(state="normal")
        text_widget.insert("end", text + "\n")
        text_widget.config(state="disabled")
        text_widget.see("end")

    def connect(self):
        """Подключение к ЭБУ"""
        port = self.port_var.get()
        baudrate = int(self.baudrate_var.get())

        try:
            self.kwp = KWP2000(port, baudrate)
            response = self.kwp.connect()

            if response.get('type') == 'response':
                self.connected = True
                self.connect_btn.configure(state="disabled")
                self.disconnect_btn.configure(state="normal")
                self.status_label.configure(
                    text="Подключено", text_color="green")
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
                self.connect_btn.configure(state="normal")
                self.disconnect_btn.configure(state="disabled")
                self.status_label.configure(text="Отключено", text_color="red")
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
                        self.append_result(
                            self.general_result,
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

        if messagebox.askyesno("Вы хотите стереть все коды ошибок?"):
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

        if messagebox.askyesno("Вы хотите выполнить сброс ЭБУ?"):
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

        selected = self.data_id_combo.get()
        data_id = int(selected.split("(0x")[1].replace(")", ""), 16)

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
        selected_device = self.control_combo.get()
        device_id = int(selected_device.split("(0x")[1].replace(")", ""), 16)

        selected_action = self.action_combo.get()
        action_map = {
            "Включить": (0x06, 0x01),  # Включить (ECO, ON)
            "Выключить": (0x06, 0x00),  # Выключить (ECO, OFF)
            "Отчет о состоянии": (0x01, None),   # Отчет (RCS)
            "Сбросить в默认ное": (0x04, None)    # Сброс (RTD)
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


if __name__ == "__main__":
    root = ctk.CTk()
    app = KWP2000GUI(root)
    root.mainloop()
