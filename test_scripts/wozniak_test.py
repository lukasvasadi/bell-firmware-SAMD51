import os
import sys
import time
import platform
import serial
from serial.tools import list_ports

# from PyQt5.QtGui import *
# from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

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
        self.lbl_gate_median = QLabel("Gate median (mV)")
        self.lbl_gate_amplitude = QLabel("Gate amplitude (mV)")
        self.lbl_freq = QLabel("Sweep frequency (mHz)")

        self.txt_reader_setting = QLineEdit("s")
        self.txt_gate_median = QLineEdit("500")
        self.txt_gate_amplitude = QLineEdit("100")
        self.txt_freq = QLineEdit("1000")

        self.btn_setup = QPushButton("Setup")

        self.reader = serial.Serial()

        # Execute main window
        self.main_window()

    def main_window(self):
        # Create layout
        self.setCentralWidget(QWidget(self))
        self.centralWidget().setLayout(self.layout)

        self.btn_setup.clicked.connect(self.main)

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


    # Bundle setup commands into readable format
    def package_setup_commands(self):
        # model = self.txt_reader_model.text()
        setting = self.txt_reader_setting.text()
        median = self.txt_gate_median.text()
        amplitude = self.txt_gate_amplitude.text()
        frequency = self.txt_freq.text()

        setup_commands = '<' + setting + ';' + median + ';' + amplitude + ';' + frequency + '>'
        print("Setup: " + setup_commands)
        return setup_commands


    # Establish serial connection
    def main(self):
        # Try automatically connecting to reader
        try:
            # Initialize port
            port = ""
            ports_available = list(list_ports.comports())
            if platform.system() == "Windows":
                for com in ports_available:
                    if "USB Serial Port" in com.description:
                        port = com[0]
            elif platform.system() == "Darwin" or "Linux":
                for com in ports_available:
                    if "FT232R USB UART" in com.description:
                        port = com[0]
            
            print(port)

            # Open reader on comport
            self.reader.port = port
            self.reader.baudrate = 500000
            self.reader.timeout = 1
            self.reader.open()

            # Toggle DTR to reset microcontroller — important for cleaning serial buffer
            self.reader.setDTR(False)
            time.sleep(0.1)
            # Wipe serial buffer
            self.reader.reset_input_buffer()
            self.reader.reset_output_buffer()
            self.reader.setDTR(True)

        except (WindowsError, AttributeError):
            err = "Error: Problem with serial connection"
            print(err)
        
        # Package and send setup commands
        setup_commands = self.package_setup_commands()
        self.reader.write(setup_commands.encode())

        time.sleep(1)

        # Print data
        while True:
            print(self.reader.readline()[0:-2].decode('utf-8'))
            time.sleep(1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    qtmodern.styles.dark(app)
    mw = qtmodern.windows.ModernWindow(window)
    mw.show()
    sys.exit(app.exec_())
