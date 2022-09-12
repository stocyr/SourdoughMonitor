# Largely copied from: https://thepoorengineer.com/en/arduino-python-plot/

import collections
import re
import time
from threading import Thread

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import serial


def calibration(val):
    return val + 0


class SerialPlot:
    def __init__(self, serial_port_name='COM4', serial_baud=115200, history_length=100):
        self.port = serial_port_name
        self.baud = serial_baud
        self.plotMaxLength = history_length
        self.line = ''
        self.line_data = collections.deque([np.nan] * history_length, maxlen=history_length)
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0
        # self.csvData = []

        print('Trying to connect to: ' + str(serial_port_name) + ' at ' + str(serial_baud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(serial_port_name, serial_baud, timeout=4)
            print('Connected to ' + str(serial_port_name) + ' at ' + str(serial_baud) + ' BAUD.')
        except Exception:
            print("Failed to connect with " + str(serial_port_name) + ' at ' + str(serial_baud) + ' BAUD.')


    def read_serial_start(self):
        if self.thread is None:
            self.thread = Thread(target=self.background_thread)
            self.thread.start()
            # Block till we start receiving values
            while not self.isReceiving:
                time.sleep(0.01)


    def get_serial_data(self, frame, lines, line_value_text, ax_bars, xpos, ypos, widths, bottom, bars, cm, time_text):
        beginning_match = re.findall(r'(\d)x(\d)', self.line)
        if beginning_match is None:
            # Filter out startup text on serial port
            return

        # Timing plotting
        current_timer = time.perf_counter()
        self.plotTimer = int((current_timer - self.previousTimer) * 1000)  # the first reading will be erroneous
        self.previousTimer = current_timer
        time_text.set_text('Plot Interval = ' + str(self.plotTimer) + 'ms')

        # Data parsing
        packets = self.line.split(' ')[1:]
        grid_x, grid_y = map(int, beginning_match[0])
        try:
            num_data = grid_x * grid_y
            distances = np.array(list(map(int, packets[:num_data])), dtype=float).reshape((grid_y, grid_x))
            confidences = np.array(list(map(int, packets[num_data:2 * num_data])), dtype=float).reshape(
                (grid_y, grid_x))
            distances[confidences < 20] = np.nan
        except ValueError:
            distances = np.ones((grid_y, grid_x)) * np.nan
            confidences = np.zeros((grid_y, grid_x))

        # Apply calibration
        distances = calibration(distances)

        # Update line plot
        neg_distance = -np.nanmean(distances)
        self.line_data.append(neg_distance)
        lines.set_data(range(self.plotMaxLength), self.line_data)
        line_value_text.set_text(f'Avg distance: {neg_distance:.1f}mm')

        # Update 3d bar plot
        # print(distances)
        heights = (- np.ravel(distances)) - bottom
        np.clip(heights, 0, None)
        intensities = np.ravel(confidences) / 255
        bars[0].remove()
        bars[0] = ax_bars.bar3d(xpos, ypos, bottom, widths, widths, heights, color=cm(intensities))

        # self.csvData.append(self.data[-1])


    def background_thread(self):  # retrieve data
        time.sleep(0.1)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while self.isRun:
            self.line = self.serialConnection.readline().decode("utf-8")
            self.isReceiving = True
            # print(self.line)


    def close(self):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')
        # df = pd.DataFrame(self.csvData)
        # df.to_csv('.../data.csv')


def main():
    port_name = 'COM4'
    baud_rate = 115200
    max_plot_history_length = 100
    plt_interval = 100  # ms

    s = SerialPlot(port_name, baud_rate, max_plot_history_length)  # initializes all required variables
    s.read_serial_start()  # starts background thread

    # Parse first packet here to figure out the SPAD pattern
    while True:
        beginning_match = re.findall(r'(\d)x(\d)', s.line)
        if beginning_match:
            break
        time.sleep(0.1)
    grid_x, grid_y = map(int, beginning_match[0])

    # Set up plotting
    xmin = 0
    xmax = max_plot_history_length
    ymin = -300
    ymax = 0
    fig = plt.figure(figsize=(10, 5))

    ax_line = fig.add_subplot(121)
    ax_line.set_xlim(xmin, xmax)
    ax_line.set_ylim(float(ymin - (ymax - ymin) / 10), float(ymax + (ymax - ymin) / 10))
    ax_line.set_title('Average distance')
    ax_line.set_xlabel("Time")
    ax_line.set_ylabel("Distance [mm]")
    time_text = ax_line.text(0.50, 0.95, '', transform=ax_line.transAxes)

    ax_bars = fig.add_subplot(122, projection='3d')
    ax_bars.set_zlim(float(ymin - (ymax - ymin) / 10), float(ymax + (ymax - ymin) / 10))
    ax_bars.set_title('Individual distances')
    ax_bars.set_xlabel('X axis')
    ax_bars.set_ylabel('Y axis')
    _xx, _yy = np.meshgrid(np.arange(grid_x), np.arange(grid_y))
    xpos, ypos = _xx.ravel(), _yy.ravel()
    widths = [0.7] * len(xpos)
    bottom = np.ones_like(xpos) * ymin
    heights = np.zeros_like(xpos)
    cm = plt.colormaps['Blues']
    bars = [ax_bars.bar3d(xpos, ypos, bottom, widths, widths, heights, color=cm(1.0), alpha=0.8)]
    ax_bars.set_ylim(ax_bars.get_ylim()[::-1])

    lines = ax_line.plot([], [], '.-', label='Avg distance')[0]
    line_value_text = ax_line.text(0.50, 0.90, '', transform=ax_line.transAxes)
    anim = animation.FuncAnimation(fig, s.get_serial_data, fargs=(lines, line_value_text, ax_bars, xpos, ypos, widths,
                                                                  bottom, bars, cm, time_text),
                                   interval=plt_interval, blit=False)
    plt.show()

    s.close()


if __name__ == '__main__':
    main()
