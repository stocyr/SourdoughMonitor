import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

df = pd.read_csv('data_012.csv', skiprows=1)
# time = pd.timedelta_range(-pd.to_timedelta(3 * len(df), 'm'), 0, len(df))
# df.index = time
'''
fig, axes = plt.subplots(2, 1, sharex=True)
axes[0].plot(df.growth, '.-', mec='white', mew=0.5)
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
'''


# Idea: twice in a row, the value must go down. the lower value must be below median by a certain margin


def peak_detect1(array, threshold: float = 0.5, window_size: int = 5) -> (int, np.ndarray):
    moving_sum = np.sum(array[:window_size - 1])
    moving_mean_array = [np.nan] * (window_size - 1)
    global_max_val = 0
    global_max_ind = -1
    for i in range(window_size - 1, len(array)):
        current_val = array[i]
        if current_val > global_max_val:
            global_max_val = current_val
            global_max_ind = i
        moving_sum += current_val
        moving_mean_array.append(moving_sum / window_size)
        if current_val < array[i - 1] < array[i - 2]:
            # Last two points have both decreased
            if moving_sum / window_size - current_val > threshold:
                return global_max_ind, np.array(moving_mean_array)
        moving_sum -= array[i - (window_size - 1)]
    else:
        return -1, np.array(moving_mean_array)


def plot_curve_with_algorithm(array: pd.Series, threshold, window_size):
    preceeding_nans = np.where(~array.isna())[0][0]
    non_nan_array = array.values[preceeding_nans:]
    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    ax.plot(non_nan_array, '.-', mec='w', mew=0.3, ms=7, lw=2)
    ax.plot(np.arange(len(non_nan_array)), pd.Series(non_nan_array).rolling(window_size).mean(), '*', alpha=0.6)
    # plt.show()
    peak_ind, moving_mean = peak_detect1(non_nan_array, threshold, window_size)
    ax.plot(np.arange(len(moving_mean)), moving_mean, '.-', alpha=0.6, lw=0.7)
    if peak_ind >= 0:
        ax.plot(peak_ind, non_nan_array[peak_ind], 'k', marker=7, ms=7)
    print(peak_ind)
    plt.show()


# plot_curve_with_algorithm(df.growth, 2.3, 5)
plot_curve_with_algorithm(df.growth, 1, 7)
