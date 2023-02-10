import matplotlib.pyplot as plt
import pandas as pd
from glob import glob
from matplotlib import ticker
import numpy as np

import sys

sys.path.append('../../')
from CIRCUITPYTHON.utils.algorithm import peak_detect

csv_files = glob('*.csv')

exclude = ['data_018.csv', 'data_021.csv']
csv_files = list(set(csv_files) - set(exclude))

fig, ax = plt.subplots()

longest_time = 0

for csv_file in csv_files:
    df = pd.read_csv(csv_file, skiprows=1)
    df.dropna(inplace=True)
    time = np.arange(len(df)) * 3 / 60
    df.index = time

    label = int(csv_file.replace('data_', '').replace('.csv', ''))
    l = ax.plot(df.index, df.growth, lw=1.3, mew=0.5, label=label)

    # Execute algorithm
    peak_ind = peak_detect(df.growth.values, threshold=1.0, window_size=7)
    if peak_ind is not None:
        ax.plot(time[peak_ind], df.growth.values[peak_ind] + 1, markeredgewidth=0, color=l[0]._color, marker=7, ms=7)
    longest_time = max(longest_time, time[-1])

ax.set_ylabel('Growth in percentage (100% = baseline)')
ax.set_xlabel('Time [h]')
ax.xaxis.set_minor_locator(ticker.MultipleLocator(1 / 4))
ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
ax.yaxis.set_major_locator(ticker.MultipleLocator(50))
ax.yaxis.set_minor_locator(ticker.MultipleLocator(25))
ax.grid(True)
ax.set_ylim(100, ax.get_ylim()[1])
ax.set_xlim(0, longest_time)
plt.title('Growth percentages vs. Hours')
plt.tight_layout()
plt.show(block=True)
