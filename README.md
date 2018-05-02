# Strace Analyzer

This repo contains scripts to record stats from the resulting files of `strace -fftttT -o strace.out <executable>` and format those stats into CSV.

## Usage

Generate strace logs for however long you like.
```
strace -fftttT -o strace.out <executable>
```
Parse the strace logs
```
./strace_analyzer.py -f strace.out.* > strace.stats
```
Convert strace stats to CSV
```
./stats_to_csv.py -f strace.stats > strace.csv
```
