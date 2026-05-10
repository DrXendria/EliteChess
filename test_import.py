"""Test CSV import parsing."""
import csv
from dialogs import PlayerListImportDialog

# Simulate reading CSV without GUI
dlg = PlayerListImportDialog.__new__(PlayerListImportDialog)
dlg._raw_data = []
dlg.map_combos = {}

# Read the test CSV
with open("sample_players.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        dlg._raw_data.append(row)

print(f"Raw rows: {len(dlg._raw_data)}")
print(f"Columns: {list(dlg._raw_data[0].keys())}")

# Test alias detection
for key, aliases in PlayerListImportDialog._ALIASES.items():
    for col in dlg._raw_data[0].keys():
        col_lower = col.lower().strip()
        if col_lower in aliases:
            print(f"  {key} -> '{col}' (exact)")
            break
        for alias in aliases:
            if alias in col_lower or col_lower in alias:
                print(f"  {key} -> '{col}' (partial: '{alias}')")
                break

print("\nALL OK!")
