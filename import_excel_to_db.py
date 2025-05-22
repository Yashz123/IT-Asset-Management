import pandas as pd
import MySQLdb

# Load the Excel file
excel_file = "ASSET LABALING.xlsx"  # Ensure this is in the same folder as the script
df = pd.read_excel(excel_file)

# Connect to MySQL
conn = MySQLdb.connect(
    host="hostname",
    user="user",
    passwd="yourpassword",
    db="db_name"
)
cursor = conn.cursor()

# Replace NaN and NaT with None
df = df.where(pd.notnull(df), None)

# Fix warranty_date: convert to string in YYYY-MM-DD or None
df['Warranty Date'] = df['Warranty Date'].apply(
    lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None
)


# Insert each row into the `assets` table
for _, row in df.iterrows():
    sql = """
    INSERT INTO assets (
        allocated_to, make, model, model_no, service_tag, department,
        office_asset_tag, host_name, ip_address, asset_status, asset_type,
        asset_description, warranty_status, warranty_date,
        functional_manager, designation, site, floor, workstation_no, category
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (
        row['Allocated To'], row['Make'], row['Model'], row['Model No'], row['Service Tag'],
        row['Department'], row['Office Asset Tag'], row['Host Name'], row['IP Address'],
        row['Asset Status'], row['Asset Type'], row['Asset Description'], row['Warranty Status'],
        row['Warranty Date'], row['Functional Manager'], row['Designation'],
        row['Site'], row['Floor'], row['Workstation No'], row['Category']
    ))

# Commit and close
conn.commit()
cursor.close()
conn.close()

print("✅ Excel data imported successfully into 'assets' table.")
