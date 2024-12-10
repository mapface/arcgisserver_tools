#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# This script cleans up ArcGIS Server quick reports on usage data for powerbi reporting 

#TODO create CLI args 

import pandas as pd
import os
from datetime import datetime

type = 'map'
new_path = r"...csv"

if type == 'map':
    master_path = r"...csv"
elif type == 'image':
    master_path = r"...csv"
else:
    raise ValueError("Invalid type! Only 'map' or 'image' are allowed.")

archive = r"..."

# Load data
master_df = pd.read_csv(master_path)
new_df = pd.read_csv(new_path)

# Timestamp for archiving the master file
file_name = os.path.splitext(os.path.split(master_path)[1])[0]
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
archived_file = os.path.join(archive, f"{file_name}_{timestamp}.csv")

# Save a copy of the original master file to the archive folder
master_df.to_csv(archived_file, index=False)
print(f"\nA copy of the original master file has been archived at '{archived_file}'")

# Ensure the 'Time_Slice' column is in datetime format
master_df['Time_Slice'] = pd.to_datetime(master_df['Time_Slice'], dayfirst=True, format='mixed')
new_df['Time_Slice'] = pd.to_datetime(new_df['Time_Slice'], dayfirst=True, format='mixed')

# Find the most recent date in the master DataFrame
most_recent_date = master_df['Time_Slice'].max()
print(f"\nMost recent date in the master file: {most_recent_date}")

# Filter the new DataFrame for rows that occur after the most recent date
new_rows = new_df[new_df['Time_Slice'] > most_recent_date]

# List the new dates being added
new_dates = new_rows['Time_Slice'].unique()
print(f"\nNew dates being added: {new_dates}")

print(f"\nNumber of new rows to be added: {len(new_rows)}")

# Append the new rows to the master DataFrame
updated_master_df = pd.concat([master_df, new_rows], ignore_index=True)

# Print message before removing rows with zero or NaN 'Request_Count'
print(f"\nRemoving rows where 'Request_Count' is 0 or NaN...")

# Remove rows where 'Request_Count' is 0 or NaN
updated_master_df_cleaned = updated_master_df[
    (updated_master_df['Request_Count'] != 0) & 
    (updated_master_df['Request_Count'].notna())
]

# Save the cleaned DataFrame to a new CSV
updated_master_df_cleaned.to_csv(master_path, index=False)
print(f"\nNew rows have been appended, cleaned, and saved to '{master_path}'\n")