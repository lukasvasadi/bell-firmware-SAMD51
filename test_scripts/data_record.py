import csv
import sys
import platform
import os
# from PyQt5.QtGui import *
# from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import serial
from serial.tools import list_ports
import time

import qtmodern.styles
import qtmodern.windows


class Window(QMainWindow):
    """
    Example for microcontroller cross-talk.
    """
    def __init__(self):
        super(Window, self).__init__()
        QApplication.setStyle(QStyleFactory.create('Plastique'))

        self.layout = QGridLayout()

        self.lbl_reader_setting = QLabel("Reader setting")
        self.lbl_gate_median = QLabel("Gate median potential (mV)")
        self.lbl_gate_amplitude = QLabel("Gate amplitude potential (mV)")
        self.lbl_freq = QLabel("Sweep frequency (mHz)")

        self.txt_reader_setting = QLineEdit("s")
        self.txt_gate_median = QLineEdit("500")
        self.txt_gate_amplitude = QLineEdit("100")
        self.txt_freq = QLineEdit("1000")

        self.btn_setup = QPushButton("Setup")

        # Execute main window
        self.main_window()

    def main_window(self):
        # Create layout
        self.setCentralWidget(QWidget(self))
        self.centralWidget().setLayout(self.layout)

        self.btn_setup.clicked.connect(self.transmit_setup)

        self.layout.addWidget(self.lbl_reader_setting, 0, 0)
        self.layout.addWidget(self.txt_reader_setting, 0, 1)

        self.layout.addWidget(self.lbl_gate_median, 1, 0)
        self.layout.addWidget(self.txt_gate_median, 1, 1)

        self.layout.addWidget(self.lbl_gate_amplitude, 2, 0)
        self.layout.addWidget(self.txt_gate_amplitude, 2, 1)

        self.layout.addWidget(self.lbl_freq, 3, 0)
        self.layout.addWidget(self.txt_freq, 3, 1)

        self.layout.addWidget(self.btn_setup, 4, 0, 1, 2)

        self.show()

    # IMPORTANT: When serial port opened, Arduino automatically resets
    def transmit_setup(self):
        if platform.system() == "Windows":
            ports_available = list(list_ports.comports())
            for com in ports_available:
                if "USB Serial Device" in com.description:
                    port = com[0]
                    print(port)
                    try:
                        # self.reader = serial.serial_for_url(port, 500000, rtscts=False, dsrdtr=False, do_not_open=True, timeout=None)
                        # self.reader.dtr = 0
                        # self.reader.rts = 0
                        # self.reader.open()

                        self.reader = serial.Serial(port=port, baudrate=500000, timeout=1)
                        self.reader.write('e'.encode())
                        time.sleep(10)
                        self.reader = serial.Serial(port=port, baudrate=500000, timeout=1)
                        # Toggle DTR to reset ATmega328 — important for cleaning serial buffer
                        self.reader.setDTR(True)
                        time.sleep(0.01)
                        # # self.reader.flushInput()
                        # # Wipe serial buffer
                        self.reader.reset_input_buffer()
                        self.reader.reset_output_buffer()
                        self.reader.setDTR(False)

                        # self.reader = serial.Serial()
                        # self.reader.port = port
                        # self.reader.baudrate = 500000
                        # self.reader.dsrdtr = True
                        # self.reader.open()
                        # self.reader.setDTR(False)
                        # time.sleep(1)
                        # self.reader.setDTR(True)
                        
                    except WindowsError:
                        print("Error: Problem with serial connection")
        else:
            reader = serial.Serial(port="com100", baudrate=500000, timeout=1)
            # Toggle DTR to reset ATmega328 — important for cleaning serial buffer
            reader.setDTR(False)
            time.sleep(0.1)
            # Wipe serial buffer
            reader.reset_input_buffer()
            # micro_controller.reset_output_buffer()
            reader.setDTR(True)

        time.sleep(1)
        transmission_incoming = True
        while transmission_incoming:
            transmission = self.reader.readline()[0:-2].decode("utf-8")
            # transmission = reader.readline().decode('ascii').strip()
            print(transmission)
            # print(transmission.decode('utf-8'))
            transmission_incoming = False

        setup_commands = self.package_setup_commands()
        self.reader.write(setup_commands.encode())

        time.sleep(1)
        transmit_data(self.reader)

    def package_setup_commands(self):
        # model = self.txt_reader_model.text()
        setting = self.txt_reader_setting.text()
        median = self.txt_gate_median.text()
        amplitude = self.txt_gate_amplitude.text()
        frequency = self.txt_freq.text()

        setup_commands = '<' + setting + ';' + median + ';' + amplitude + ';' + frequency + '>'
        print("Setup: " + setup_commands)
        return setup_commands


def transmit_data(reader):
    fieldnames = ['time', 'sen1Ch1', 'sen1Ch2', 'sen1Ch3', 'sen1Ch4', 'sen1Ch5',
                  'sen2Ch1', 'sen2Ch2', 'sen2Ch3', 'sen2Ch4', 'sen2Ch5', 'cnt1', 'cnt2']
    with open('data.csv', 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(fieldnames)

    while True:
        with open('data.csv', 'a', newline='') as csv_file:
            # csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            time_start = time.time()
            transmission = reader.readline()[0:-2].decode('utf-8')
            print(transmission)
            data = transmission.split(',')
            # csv_writer.writerow([data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7],
            #                      data[8], data[9], data[10], data[11]])
            # print(time.time() - time_start)
            time.sleep(1)

            if not transmission:
                print("Finished")
                break


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    qtmodern.styles.dark(app)
    mw = qtmodern.windows.ModernWindow(window)
    mw.show()
    sys.exit(app.exec_())
