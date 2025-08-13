import pandas as pd
import sqlite3

# Read the data from our CSV file
df = pd.read_csv("employees.csv")

# Connect to a new SQLite database file
# This will create the file if it doesn't exist
conn = sqlite3.connect("company_database.db")

# Write the data from the DataFrame into a table named 'employees'
df.to_sql("employees", conn, if_exists="replace", index=False)

# Close the connection
conn.close()

print("Database 'company_database.db' with table 'employees' created successfully!")