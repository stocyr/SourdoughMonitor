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

fig, ax = plt.subplots()

floor = 160
normal_height = 24

all_heights = floor - df[[f'd{i}' for i in range(9)]]
rolling_mean = all_heights.mean(axis=1).rolling(5).mean()
subsampled = rolling_mean.loc[valid_indices]
subsampled_percentages = subsampled / normal_height * 100
ax.plot(df.sec[valid_indices], subsampled_percentages, 'C0', lw=2, label='Simulated data')

new_df = pd.DataFrame({'time': df.sec[valid_indices], 'percentages': subsampled_percentages.values})
new_df.to_csv('./fake_data.csv', index=False)

formatter = ticker.FuncFormatter(timeTicks)
ax.xaxis.set_major_formatter(formatter)
ax.xaxis.set_major_locator(ticker.MultipleLocator(60 * 60))
plt.xlim(0, df.sec.max())
plt.legend()
plt.tight_layout()
plt.show()
