from time import time

# I don't generally like use fractional seconds, but you're free to
# by removing the int() cast
df['EventTime'] = float(int(time()))
df['RecordID'] = df.reset_index(drop=True).index.astype(str) + '_' + df['EventTime'].astype(str)
