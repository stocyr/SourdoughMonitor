import datetime

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import ticker
import numpy as np


def timeTicks(x, pos):
    seconds = x
    d = datetime.timedelta(seconds=seconds)
    return f'{str(d).split(":")[0]}h'


df = pd.read_csv('fake_data.csv')

exp_history = df.percentages.ewm(alpha=0.3).mean()
mean_history = df.percentages.rolling(10).mean()
median_history = df.percentages.rolling(10).median()

fig, ax = plt.subplots()
plt.plot(df.time, df.percentages)
plt.plot(df.time, exp_history)
plt.plot(df.time, mean_history)
plt.plot(df.time, median_history)

formatter = ticker.FuncFormatter(timeTicks)
ax.xaxis.set_major_formatter(formatter)
ax.xaxis.set_major_locator(ticker.MultipleLocator(60 * 60))
plt.xlim(0, df.time.max())
plt.legend()
plt.tight_layout()
plt.show()
