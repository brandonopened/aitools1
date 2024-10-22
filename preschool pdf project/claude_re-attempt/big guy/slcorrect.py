import csv
from collections import defaultdict

def correct_smartlevels(input_file, output_file):
    # Read the CSV file
    with open(input_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)

    # Initialize variables to track levels
    current_levels = defaultdict(int)
    max_depth = 0

    # First pass: determine the maximum depth
    for row in data:
        depth = len(row['type'].split())
        max_depth = max(max_depth, depth)

    # Second pass: correct smartlevels
    for row in data:
        type_parts = row['type'].split()
        depth = len(type_parts)

        # Reset lower levels when a higher level changes
        for i in range(depth, max_depth + 1):
            current_levels[i] = 0

        # Increment the current level
        current_levels[depth] += 1

        # Build the new smartlevel
        new_smartlevel = '.'.join(str(current_levels[i]) for i in range(1, depth + 1))
        row['smartlevel'] = new_smartlevel

    # Write the corrected data back to a new CSV file
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    print(f"Corrected CSV has been written to {output_file}")

# Usage
input_file = 'ms_infant_toddler.csv'
output_file = 'ms-standards-csv-corrected.csv'
correct_smartlevels(input_file, output_file)