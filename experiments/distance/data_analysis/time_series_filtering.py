import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import ticker


def timeTicks(x, pos):
    seconds = x
    d = datetime.timedelta(seconds=seconds)
    return f'{str(d).split(":")[0]}h'


df = pd.read_csv(r'log_data.csv')  # , parse_dates=['timestamp'], index_col='timestamp')
df.index = pd.TimedeltaIndex(df.timestamp)
df['sec'] = df.index.total_seconds()

interval = 5 * 60 * 3

valid_indices = df.index[np.arange(len(df)) % interval == (interval - 1)]

data = 120 - df.d4

configs = [
    (5,),
    (5 * 2 - 1,),
    (5 * 3,),
    (5 * 9,),
]

fig, axes = plt.subplots(len(configs), 1, sharex=True, sharey=True)

for i, ax in enumerate(axes):
    rolling_median = data.rolling(configs[i][0]).mean()
    subsampled = rolling_median.loc[valid_indices]

    ax.plot(df.sec, data, 'C0', alpha=0.3, lw=2)
    ax.twinx().plot(df.sec, df.c4, 'C2')
    ax.plot(df.sec, rolling_median, 'C0', lw=0.5)
    ax.plot(df.sec[valid_indices], subsampled, '.-C1')

formatter = ticker.FuncFormatter(timeTicks)
axes[-1].xaxis.set_major_formatter(formatter)
axes[-1].xaxis.set_major_locator(ticker.MultipleLocator(60 * 60))
axes[-1].set_xlim(0, df.sec.max())
plt.ylim(0, 30)
plt.tight_layout()
plt.show()

fig, ax = plt.subplots()
for i in range(9):
    data = 120 - df[f'd{i}']
    rolling_median = data.rolling(10).median()
    subsampled = rolling_median.loc[valid_indices]
    ax.plot(df.sec[valid_indices], subsampled, label=f'Area {i}')

formatter = ticker.FuncFormatter(timeTicks)
ax.xaxis.set_major_formatter(formatter)
ax.xaxis.set_major_locator(ticker.MultipleLocator(60 * 60))
plt.xlim(0, df.sec.max())
plt.legend()
plt.tight_layout()
plt.show()


fig, ax = plt.subplots()
for i in range(9):
    data = 120 - df[f'd{i}']
    rolling_median = data.rolling(10).median()
    subsampled = rolling_median.loc[valid_indices]
    ax.plot(df.sec[valid_indices], subsampled, 'k', alpha=0.2)

all_distances = 120 - df[[f'd{i}' for i in range(9)]]
rolling_median = all_distances.mean(axis=1).rolling(10).median()
subsampled = rolling_median.loc[valid_indices]
ax.plot(df.sec[valid_indices], subsampled, 'C0', lw=2, label='Processed avg')

rolling_median_all = all_distances.rolling(10).median()
subsampled = rolling_median_all.loc[valid_indices]
subsampled_mean = subsampled.mean(axis=1)
ax.plot(df.sec[valid_indices], subsampled_mean, 'C1', lw=2, label='Avg of processed')

formatter = ticker.FuncFormatter(timeTicks)
ax.xaxis.set_major_formatter(formatter)
ax.xaxis.set_major_locator(ticker.MultipleLocator(60 * 60))
plt.xlim(0, df.sec.max())
plt.legend()
plt.tight_layout()
plt.show()
