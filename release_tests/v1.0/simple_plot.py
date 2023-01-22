import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

df = pd.read_csv('data_011.csv', skiprows=1)
# time = pd.timedelta_range(-pd.to_timedelta(3 * len(df), 'm'), 0, len(df))
# df.index = time

fig, axes = plt.subplots(2, 1, sharex=True)
axes[0].plot(df.growth)
growth_diff_ax = axes[0].twinx()
growth_diff_ax.plot(np.diff(df.growth, prepend=np.nan), 'C1')

axes[1].plot(df.temp)
temp_diff_ax = axes[1].twinx()
temp_diff_ax.plot(np.diff(df.temp, prepend=np.nan), 'C1')

plt.show(block=True)
