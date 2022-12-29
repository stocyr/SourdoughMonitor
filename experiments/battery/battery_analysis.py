import seaborn as sns
import matplotlib.pyplot as plt
import datetime
import pandas as pd
from matplotlib import ticker


def timeTicks(x, pos):
    seconds = x
    d = datetime.timedelta(seconds=seconds)
    return f'{str(d).split(":")[0]}h'


sns.set_style('darkgrid')

df = pd.read_csv('battery.csv')
df.index = pd.TimedeltaIndex(df.timestamp)
df['sec'] = df.index.total_seconds()

fig, ax = plt.subplots()

ax.plot(df.sec, df.percentage, 'C0', label='Battery percentage')
axt = ax.twinx()
axt.plot(df.sec, df.voltage, 'C1', label='Battery voltage')
ax.legend(loc='lower left')
axt.legend(loc='upper right')

formatter = ticker.FuncFormatter(timeTicks)
ax.xaxis.set_major_formatter(formatter)
ax.xaxis.set_major_locator(ticker.MultipleLocator(60 * 60))
ax.set_xlim(0, df.sec.max())
plt.show(block=True)
