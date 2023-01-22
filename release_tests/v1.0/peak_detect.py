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
growth_diff_ax.grid(True)

axes[1].plot(df.growth)
axes[1].plot(df.growth.rolling(5).mean(), 'C1')
med = df.growth.rolling(5).median()
axes[1].step(med, 'C2')

falling = np.diff(med, prepend=np.nan) < -0.3
axes[1].plot(med.iloc[falling], 'C3o')

plt.show(block=True)

# Idea: twice in a row, the value must go down. the lower value must be below median by a certain margin
