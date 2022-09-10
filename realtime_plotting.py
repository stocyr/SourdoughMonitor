import collections
import time
from threading import Thread

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import serial


class serialPlot:
    def __init__(self, serialPort='COM4', serialBaud=115200, plotLength=100):
        self.port = serialPort
        self.baud = serialBaud
        self.plotMaxLength = plotLength
        self.line = ''
        self.data = collections.deque([0.0] * plotLength, maxlen=plotLength)
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0
        # self.csvData = []

        print('Trying to connect to: ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(serialPort, serialBaud, timeout=4)
            print('Connected to ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        except:
            print("Failed to connect with " + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')


    def readSerialStart(self):
        if self.thread == None:
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            # Block till we start receiving values
            while self.isReceiving != True:
                time.sleep(0.1)


    def getSerialData(self, frame, lines, lineValueText, lineLabel, timeText):
        currentTimer = time.perf_counter()
        self.plotTimer = int((currentTimer - self.previousTimer) * 1000)  # the first reading will be erroneous
        self.previousTimer = currentTimer
        timeText.set_text('Plot Interval = ' + str(self.plotTimer) + 'ms')
        try:
            values = [int(distance[:-2]) for distance in self.line.split(' ')[:9]]
            value = sum(values) / len(values)
        except ValueError:
            value = 0.0
        self.data.append(value)  # we get the latest data point and append it to our array
        lines.set_data(range(self.plotMaxLength), self.data)
        lineValueText.set_text(f'{lineLabel} = {value:.0f}mm')
        # self.csvData.append(self.data[-1])


    def backgroundThread(self):  # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while (self.isRun):
            self.line = self.serialConnection.readline().decode("utf-8")
            self.isReceiving = True
            print(self.line)


    def close(self):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')
        # df = pd.DataFrame(self.csvData)
        # df.to_csv('/home/rikisenia/Desktop/data.csv')


def main():
    portName = 'COM4'
    baudRate = 115200
    maxPlotLength = 100
    s = serialPlot(portName, baudRate, maxPlotLength)  # initializes all required variables
    s.readSerialStart()  # starts background thread

    # plotting starts below
    pltInterval = 100  # Period at which the plot animation updates [ms]
    xmin = 0
    xmax = maxPlotLength
    ymin = 0
    ymax = 1000
    fig = plt.figure()
    ax = plt.axes(xlim=(xmin, xmax), ylim=(float(ymin - (ymax - ymin) / 10), float(ymax + (ymax - ymin) / 10)))
    ax.set_title('Real time Display')
    ax.set_xlabel("time")
    ax.set_ylabel("Distance [mm]")

    lineLabel = 'Distance'
    timeText = ax.text(0.50, 0.95, '', transform=ax.transAxes)
    lines = ax.plot([], [], '.-', label=lineLabel)[0]
    lineValueText = ax.text(0.50, 0.90, '', transform=ax.transAxes)
    anim = animation.FuncAnimation(fig, s.getSerialData, fargs=(lines, lineValueText, lineLabel, timeText),
                                   interval=pltInterval)  # fargs has to be a tuple

    plt.legend(loc="upper left")
    plt.show()

    s.close()


if __name__ == '__main__':
    main()
