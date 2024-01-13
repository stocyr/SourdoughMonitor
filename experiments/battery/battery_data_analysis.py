import pandas as pd

# Step 1: Read the CSV using pandas
file_path = 'experiments/battery/influxdata_2024-01-13T14_27_57Z.csv'
df = pd.read_csv(file_path, skiprows=3)

# Step 2: Parse the timestamp
df['time'] = pd.to_datetime(df['time'])

# Step 3: Sort the values by date
df = df.sort_values(by='time')

# Step 4: Export to "all_data.csv"
df.to_csv('experiments/battery/influxdata_all_data.csv', index=False)

# Step 5: Extract only the battery data, stripping off any None rows
battery_df = df[['time', 'battery_level']].dropna()

# Step 6: Export battery data to "battery_data.csv"
battery_df.to_csv('experiments/battery/influxdata_battery_data.csv', index=False)
