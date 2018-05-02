#!/usr/bin/env python3
import json

def main(args):
    with open(args.filename) as f:
        stats = json.load(f)
    column_names = ["timestamp"]
    data = []
    for bucket in stats:
        calls = stats[bucket]["calls"]
        row = [0 for i in range(len(column_names))]
        row[0] = bucket
        for call in calls:
            if call not in column_names:
                column_names.append(call)
                row.append(0)
            row[column_names.index(call)] = calls[call]["total_duration"]/calls[call]["count"]
        data.append(row)
    print(','.join(str(name) for name in column_names))
    for row in data:
        while len(row) < len(column_names):
            row.append(0)
        print(','.join(str(point) for point in row))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Converts strace stats to gnu plot format')
    parser.add_argument('-f', dest='filename')
    args = parser.parse_args()
    main(args)
