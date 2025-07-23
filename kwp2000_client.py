import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from serial import Serial, SerialException
import time
from enum import Enum


class KWP2000:
    def __init__(self, port, baudrate=10400):
        self.ser = Serial(port=port, baudrate=baudrate,
                          bytesize=8, parity='N', stopbits=1,
                          timeout=1)

        # Адреса согласно спецификации
        self.ECU_ADDRESS = 0x10
        self.TESTER_ADDRESS = 0xF1

        # Временные параметры
        self.P1_MAX = 0.020  # 20 мс
        self.P2_MIN = 0.025  # 25 мс
        self.P2_MAX = 0.050  # 50 мс
        self.P3_MIN = 0.100  # 100 мс
        self.P3_MAX = 5.000  # 5000 мс
        self.P4_MAX = 0.020  # 20 мс

    def connect(self):
        """Инициализация соединения с быстрой инициализацией"""
        # Быстрая инициализация согласно спецификации
        self.ser.setDTR(False)
        time.sleep(0.025)  # TiniL = 25±1 ms
        self.ser.setDTR(True)
        time.sleep(0.050)  # TWuP = 50±1 ms

        # Отправка запроса startCommunication
        response = self.start_communication()
        time.sleep(0.5)
        response = self.start_dignostic_session()
        time.sleep(0.5)
        response = self.tester_present()
        return response

    def build_header(self, length, has_length_byte=False):
        """Построение заголовка"""
        if has_length_byte:
            # 4-байтный заголовок
            fmt = 0x80 | (length & 0x3F)  # A1=1, A0=0
            header = bytes(
                [fmt, self.ECU_ADDRESS, self.TESTER_ADDRESS, length])
        else:
            # 3-байтный заголовок
            fmt = 0x80 | (length & 0x3F)
            header = bytes([fmt, self.ECU_ADDRESS, self.TESTER_ADDRESS])
        return header

    def calculate_checksum(self, data):
        """Расчет контрольной суммы (8-битная сумма всех байт)"""
        return sum(data) & 0xFF

    def send_request(self, service_id, data=b'', has_length_byte=False):
        """Отправка запроса и получение ответа"""
        # Построение сообщения
        message_data = bytes([service_id]) + data
        length = len(message_data)

        header = self.build_header(length, has_length_byte)
        message = header + message_data
        checksum = self.calculate_checksum(message)
        full_message = message + bytes([checksum])

        print(f"Отправка: {full_message.hex().upper()}")

        # Отправка сообщения
        self.ser.reset_input_buffer()
        self.ser.write(full_message)

        # Задержка перед чтением ответа
        time.sleep(0.5)  # Подберите оптимальное значение
        # Чтение ответа
        self.ser.read(len(full_message))
        response = self.ser.read_all()
        print(
            f"Получено: {response.hex().upper() if response else 'Нет ответа'}")

        # Проверка контрольной суммы
        if len(response) > 0:
            received_checksum = response[-1]
            calculated_checksum = self.calculate_checksum(response[:-1])

            if received_checksum != calculated_checksum:
                raise ValueError("Неверная контрольная сумма в ответе")

        return response

    def parse_response(self, response):
        """Разбор ответа от ЭБУ"""
        if len(response) < 4:
            raise ValueError("Слишком короткий ответ")

        # Проверка на отрицательный ответ (0x7F)
        if response[3] == 0x7F:
            service_id = response[4]
            error_code = response[5]
            return {'type': 'error',
                    'service_id': service_id,
                    'error_code': error_code}
        else:
            # Положительный ответ
            # Преобразование ID ответа в ID запроса
            service_id = response[3] - 0x40
            data = response[4:-1]  # Исключаем заголовок и контрольную сумму
            return {'type': 'response', 'service_id': service_id, 'data': data}

    # Базовые сервисы KWP2000
    def start_communication(self):
        """Сервис StartCommunication (0x81)"""
        response = self.send_request(0x81)
        return self.parse_response(response)

    def start_dignostic_session(self, session_type=0x81, baudrate=0x0A):
        """Сервис start_dignostic_session (0x81)"""
        response = self.send_request(0x10, bytes([session_type, baudrate]))
        return self.parse_response(response)

    def stop_dignostic_session(self):
        """Сервис start_dignostic_session (0x81)"""
        response = self.send_request(0x20)
        return self.parse_response(response)

    def stop_communication(self):
        """Сервис StopCommunication (0x82)"""
        response = self.send_request(0x82)
        return self.parse_response(response)

    def ecu_reset(self, reset_type=0x01):
        """Сервис ECUReset (0x11)
           reset_type: 0x01 - powerOn (аналог цикла включения зажигания)
        """
        response = self.send_request(0x11, bytes([reset_type]))
        return self.parse_response(response)

    def read_ecu_identification(self, ident_type=0x80):
        """Сервис ReadEcuIdentification (0x1A)
           ident_type: 0x80 - полная таблица идентификационных данных
        """
        response = self.send_request(0x1A, bytes([ident_type]))
        return self.parse_response(response)

    def read_dtc_by_status(self, status=0x00, group=0x0000):
        """Сервис ReadDiagnosticTroubleCodesByStatus (0x18)"""
        data = bytes([status]) + bytes([group >> 8, group & 0xFF])
        response = self.send_request(0x18, data)
        return self.parse_response(response)

    def clear_dtc(self, group=0x0000):
        """Сервис ClearDiagnosticInformation (0x14)"""
        data = bytes([group >> 8, group & 0xFF])
        response = self.send_request(0x14, data)
        return self.parse_response(response)

    def read_data_by_local_id(self, local_id):
        """Сервис ReadDataByLocalIdentifier (0x21)"""
        response = self.send_request(0x21, bytes([local_id]))
        return self.parse_response(response)

    def tester_present(self, response_required=0x01):
        """Сервис TesterPresent (0x3E)"""
        response = self.send_request(0x3E, bytes([response_required]))
        return self.parse_response(response)

    def read_memory_by_address(self, memory_type, address, size):
        """Сервис ReadMemoryByAddress (0x23)"""
        data = bytes([memory_type]) + \
            bytes([address >> 8, address & 0xFF]) + bytes([size])
        response = self.send_request(0x23, data, has_length_byte=True)
        return self.parse_response(response)

    def write_data_by_local_id(self, local_id, data):
        """Сервис WriteDataByLocalIdentifier (0x3B)"""
        response = self.send_request(0x3B, bytes([local_id]) + data)
        return self.parse_response(response)

    def input_output_control(self, io_id, control_param, control_data=b''):
        """Сервис InputOutputControlByLocalIdentifier (0x30)"""
        data = bytes([io_id, control_param]) + control_data
        response = self.send_request(0x30, data)
        return self.parse_response(response)

    def close(self):
        """Закрытие соединения"""
        self.ser.close()


class DTCStatus(Enum):
    """Статусы кодов неисправностей"""
    TEST_FAILED = 0x80
    TEST_FAILED_THIS_OPERATION_CYCLE = 0x40
    PENDING_DTC = 0x20
    CONFIRMED_DTC = 0x10
    TEST_NOT_COMPLETED_SINCE_LAST_CLEAR = 0x08
    TEST_FAILED_SINCE_LAST_CLEAR = 0x04
    TEST_NOT_COMPLETED_THIS_OPERATION_CYCLE = 0x02
    WARNING_INDICATOR_REQUESTED = 0x01


class KWPUtils:
    @staticmethod
    def parse_dtcs(response_data):
        """Разбор списка DTC из ответа на ReadDTCByStatus"""
        if not response_data or len(response_data) < 1:
            return []

        num_dtc = response_data[0]
        dtcs = []

        for i in range(num_dtc):
            offset = 1 + i * 3
            dtc_high = response_data[offset]
            dtc_low = response_data[offset + 1]
            status = response_data[offset + 2]

            # Формирование кода неисправности в формате PXXXX
            dtc_code = f"P{dtc_high:02X}{dtc_low:02X}"

            # Разбор статуса
            status_flags = []
            for flag in DTCStatus:
                if status & flag.value:
                    status_flags.append(flag.name)

            dtcs.append({
                'code': dtc_code,
                'status': status,
                'status_flags': status_flags
            })

        return dtcs

    @staticmethod
    def parse_identification(response_data):
        """Разбор данных идентификации ЭБУ"""
        if not response_data or len(response_data) < 1:
            return {}

        ident_type = response_data[0]
        result = {}

        if ident_type == 0x80:  # Полная таблица идентификации
            # VIN (19 байт)
            vin = response_data[1:20].decode('ascii', errors='ignore')
            result['VIN'] = vin

            # Прочие данные согласно спецификации
            # (аналогично для других полей)

        return result

    @staticmethod
    def parse_ass_params(response_data):
        """Разбор параметров After Sales Service (RLI_ASS)"""
        if not response_data or len(response_data) < 36:
            return {}

        params = {}

        # Комплектация 1
        equip1 = response_data[2]
        params['Датчик кислорода'] = bool(equip1 & 0x01)
        params['Адсорбер'] = bool(equip1 & 0x02)
        # ... другие флаги комплектации

        # Температура охлаждающей жидкости
        coolant_temp = response_data[10] - 40
        params['Температура ОЖ'] = f"{coolant_temp} °C"

        # Обороты двигателя
        rpm = response_data[13] * 40
        params['Обороты'] = f"{rpm} об/мин"

        # Напряжение бортсети
        voltage = 5.2 + response_data[20] * 0.05
        params['Бортовое напряжение'] = f"{voltage:.2f} В"

        # ... другие параметры согласно спецификации

        return params

# Далее идет класс KWP2000GUI (как в предыдущем примере)
# ... [полный код класса KWP2000GUI из предыдущего примера] ...


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


if __name__ == "__main__":
    root = tk.Tk()
    app = KWP2000GUI(root)
    root.mainloop()
