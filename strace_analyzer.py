#!/usr/bin/env python3
import json
import re
import time
import os
import sys
from multiprocessing import Pool
import multiprocessing

signal_line_parser = re.compile('^([0-9]+\.[0-9]+) --- ([A-Z]+) \{si_signo=([A-Z]+), si_code=([A-Z_]+), si_pid=([0-9]+), si_uid=([0-9]+)\} --- *$')
line_parser = re.compile('^([0-9]+\.[0-9]+) ([a-zA-Z0-9_]+)\((.*)\) += ([\-0-9xa-f?]+)( [\(\)a-zA-Z_0-9: ]+){0,1} <([0-9]+\.[0-9]+)>$')

def parse_line(line):
    match = signal_line_parser.match(line)
    if match != None:
        return {
            "is_signal": True,
            "timestamp": float(match.group(1)),
            "signal": match.group(2),
            "si_signo": match.group(3),
            "si_code": match.group(4),
            "si_pid": int(match.group(5)),
            "si_uid": int(match.group(6))
        }
    match = line_parser.match(line)
    if match == None:
        return None
    exit_state = match.group(5)
    if exit_state != None:
        exit_state = exit_state[1:]
    return {
        "is_signal": False,
        "timestamp": float(match.group(1)),
        "call": match.group(2),
        "args": match.group(3),
        "return_code": match.group(4),
        "exit_state": exit_state,
        "duration": float(match.group(6))
    }

class StraceRecorder:
    def __init__(self, filename, bucket_length_seconds = 300):
        self.filename = filename
        self.bucket_length = bucket_length_seconds
        self.buckets = {}

    def record_stats(self, record):
        if record == None:
            return
        record["bucket"] = str(record["timestamp"] // self.bucket_length * self.bucket_length)
        if record["bucket"] not in self.buckets:
            self.buckets[record["bucket"]] = {
                "events": {},
                "calls": {}
            }
        if record["is_signal"]:
            self._record_signal(record)
        else:
            self._record_call(record)

    def stats(self):
        return self.buckets

    def join(self, recorder):
        for bucket in recorder.buckets:
            if bucket not in self.buckets:
                self.buckets[bucket] = recorder.buckets[bucket]
                continue
            for event in recorder.buckets[bucket]["events"]:
                if event not in self.buckets[bucket]["events"]:
                    self.buckets[bucket]["events"][event] = recorder.buckets[bucket]["events"][event]
                    continue
                self.buckets[bucket]["events"][event] += recorder.buckets[bucket]["events"][event]
            for call in recorder.buckets[bucket]["calls"]:
                if call not in self.buckets[bucket]["calls"]:
                    self.buckets[bucket]["calls"][call] = recorder.buckets[bucket]["calls"][call]
                    continue
                self.buckets[bucket]["calls"][call]["total_duration"] += recorder.buckets[bucket]["calls"][call]["total_duration"]
                self.buckets[bucket]["calls"][call]["count"] += recorder.buckets[bucket]["calls"][call]["count"]

    def _record_signal(self, record):
        if record["signal"] not in self.buckets[record["bucket"]]["events"]:
            self.buckets[record["bucket"]]["events"][record["signal"]] = 1
        else:
            self.buckets[record["bucket"]]["events"][record["signal"]] += 1

    def _record_call(self, record):
        bucket = self.buckets[record["bucket"]]
        if record["call"] not in bucket["calls"]:
            bucket["calls"][record["call"]] = {
                "total_duration": record["duration"],
                "count": 1
            }
        else:
            bucket["calls"][record["call"]]["total_duration"] += record["duration"]
            bucket["calls"][record["call"]]["count"] += 1

def process_file(filename):
    recorder = StraceRecorder(filename)
    current_line = 0
    file_size = os.path.getsize(filename)
    bytes_processed = 0
    with open(filename) as f:
        for line in f:
            if current_line % 100000 == 0:
                print("{}: {}".format(filename, bytes_processed/file_size), file=sys.stderr)
            recorder.record_stats(parse_line(line))
            bytes_processed += len(line)
            current_line += 1
    return recorder

def main(args):
    threads = []
    stats = []
    pool = Pool(multiprocessing.cpu_count())
    for filename in args.files:
        threads.append(pool.apply_async(process_file, args=(filename,)))
    for thread in threads:
        stats.append(thread.get())
    recorder = stats[0]
    for r in stats[1:]:
        recorder.join(r)
    print(json.dumps(recorder.stats()))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A parser for strace -T logs")
    parser.add_argument('-f', '--strace-files', nargs='+', dest='files', help='The log files to parse', required=True)

    args = parser.parse_args()
    main(args)
