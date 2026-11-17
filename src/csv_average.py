# -*- coding: utf-8 -*-
"""
Created on Mon Nov 16 14:57:18 2026

@author: map25bg

This code takes files from csv_extract and take an average across a rolling region where the std is less than a value of the mean
It works out the longest regions over both Ff and Fz and finds these averages. So that the steady-state region is only taken if they are both stable
These are then saved to a summary file. 
I would recommend making a copy of all the extracted_steps files you want to be in your summary if they have come from accross different tests and saving them in a plotting folder so it is all in one place.

Arguments available to parse in console:
        files = specific csv file(s) to process
        -f / --folder = folder of extracted_csv files to process
        -o / --output = summary csv to write to 
        --grouping = global grouping within the folder to process (eg. -- grouping "*tool3_*.csv")
        -r / --redo = redo the files that are already in the summary file (eg. --redo)
Claude AI was used to complete this code
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import csv


#configure the file: 
    
input_folder = Path("extracted")
summary_file = Path("summary.csv")

time_col = "T"
Fz_col = "Fz"
Ff_col = "Ff"
is_cycle = "Cycles"     #"Cycle" if the file contains a cycle, else None

window_s = 3.0      # rolling window length (s)
tol_fz = 0.1       # Fz steady if the rolling std <10% of rolling mean
tol_ff = 0.1      # Ff steady if the rolling std <10% of rolling mean
min_steady_s = 5.0  # minimum steady region length (s)

trim_start = 0.2    # fallback: drop first 20%
trim_end = 0.1      # fallback: drop last 10%


def parse_filename(stem):
    parts = stem.split("_")
    return{
        "run": parts[0] if len(parts) > 0 else "unknown",
        "tool": "_".join(parts[1:3]) if len(parts) > 2 else "unknown"}


def stable_mask(series, win, tol):  #mask replaces the values of rows where a condition evaluates to True
    """ True whenever the rolling std is below tol * |rolling mean|"""
    roll_mean = series.rolling(win, center = True).mean()
    roll_std = series.rolling(win, center = True).std()
    with np.errstate(divide="ignore", invalid="ignore"):
        mask = (roll_std / roll_mean.abs()) < tol
    return mask.fillna(False).to_numpy()


def longest_true_run(mask):
    """Returns (start, end) indices (end exclusive) of the longest True run. (True satisfies the stable region)"""
    best_start, best_len = 0, 0
    cur_start = None
    for i, m in enumerate(mask):
        if m and cur_start is None:
            cur_start = i
        if cur_start is not None and (not m or i == len(mask) - 1):
            end = i if not m else i + 1
            if end - cur_start > best_len:
                best_start, best_len = cur_start, end - cur_start
            cur_start = None
    return best_start, best_start +  best_len


def find_steady_region(df, tol_fz, tol_ff, window_s, min_steady_s):
    """longest stretch where BOTH Fz and Ff re stable. Returns (start, end) or None"""
    dt = np.median(np.diff(df[time_col].to_numpy()))
    win = max(int(window_s/ dt), 3)
    
    both = stable_mask(df[Fz_col], win, tol_fz) & stable_mask(df[Ff_col], win, tol_ff)
    s, e = longest_true_run(both)
    
    if (e-s) * dt < min_steady_s:
        return None
    else:
        return s, e
    
def fixed_trim_region(df):
    n = len(df)
    return int(n* trim_start), int(n * (1 - trim_end))

def region_from_times(df, t0, t1):
    t = df[time_col].to_numpy()
    s = int(np.searchsorted(t, t0))
    e = int(np.searchsorted(t, t1, side="right"))
    return s, max(e, s+1)



#Plotting what has just been done for manual confirmation of Steady State Region

def show_check_plot(df, region, title):
    t  = df[time_col]
    fig, (ax1, ax2) = plt.subplots(2,1, sharex=True, figsize=(10, 6))
    
    for ax, col, colour in ((ax1, Fz_col, "tab:blue"), (ax2, Ff_col, "tab:red")):
        ax.plot(t, df[col], color=colour, lw=0.8)
        ax.set_ylabel(col)
        ax.grid(alpha=0.3)
        
    if region is not None:
        s, e = region
        t0, t1 = t.iloc[s], t.iloc[e-1]
        for ax, col in ((ax1, Fz_col), (ax2, Ff_col)):
            ax.axvspan(t0, t1, color="gold", alpha=0.3)
            m = df[col].iloc[s:e].mean()
            ax.hlines(m, t0, t1, colors="k", linestyles="--", lw=1.2)
            ax.set_title(f"{col} mean in window = {m:.4g}", fontsize=9, loc="right")
            
    ax2.set_xlabel(time_col)
    fig.suptitle(title)
    fig.tight_layout()
    plt.show(block=False)
    plt.pause(0.1)
    return fig


#Summary row
def make_row(df, region, path, method, cycle=None, settings=None):
    s, e =region
    seg = df.iloc[s:e]
    fz, ff = seg[Fz_col], seg[Ff_col]
    row = {
        "file": Path(path).name,
        **parse_filename(Path(path).stem)}
    
    if cycle is not None:
        row["cycle"] = cycle
    row.update({
        "Fz_mean": fz.mean(),
        "Fz_std": fz.std(),
        "Ff_mean": ff.mean(),
        "Ff_std": ff.std(),
        "COF": abs(ff.mean() / fz.mean()) if fz.mean() != 0 else np.nan,
        "num_points": len(seg),
        "t_start": df[time_col].iloc[s],
        "t_end": df[time_col].iloc[e-1],
        "method": method,})
    
    if method == "auto":
        row.update({
            "Fz_tolerance": settings["tol_fz"],
            "Ff_tolerance": settings["tol_ff"],
            "window_s": settings["window_s"],
            "min_steady_region_s": settings["min_steady_s"],})
    else:
         row.update({
            "start_trim": trim_start,
            "end_trim": trim_end,}
        )
    
    return row

def save_row(row):
    """adding the row to summary.csv or replacing any earlier row with the same filename/cycle"""
    new = pd.DataFrame([row])
    if summary_file.exists():
        old = pd.read_csv(summary_file)
        keys = ["file"] + (["cycle"] if "cycle" in row else [])
        if all (k in old.columns for k in keys):
            mask = np.ones(len(old), dtype=bool)
            for k in keys:
                mask &= (old[k].astype(str)==str(row[k])).to_numpy()
            old = old[~mask]
        new = pd.concat([old,new], ignore_index=True)
    new.to_csv(summary_file, index = False)
    
    
# Interactive review of one segment (a file, or one cycle of a file)
def review_segment(df, path, label, cycle=None):
    """Returns 'saved', 'skipped' or 'quit'."""
    use_tol_fz, use_tol_ff, win_s, min_s = tol_fz, tol_ff, window_s, min_steady_s

    region = find_steady_region(df, use_tol_fz, use_tol_ff, win_s, min_s)
    method = "auto"
    if region is None:
        region = fixed_trim_region(df)
        method = "fixed_trim"

    while True:
        fig = show_check_plot(df, region, f"{label}   [{method}]")
        print(f"\n{label}   method: {method}")
        print(f"tolerances: Fz {use_tol_fz:.0%}, Ff {use_tol_ff:.0%}, window {win_s}s")
        choice = input(
            "  [y] accept  [n] skip  [t] change tolerances  "
            "[m] enter window manually  [f] fixed trim  [q] quit : "
        ).strip().lower()
        plt.close(fig)

        if choice == "y":
            settings = {"tol_fz": use_tol_fz,
                        "tol_ff": use_tol_ff,
                        "window_s": win_s,
                        "min_steady_s": min_s}
            save_row(make_row(df, region, path, method, cycle, settings))
            print("  saved.")
            return "saved"

        if choice == "n":
            print("  skipped.")
            return "skipped"

        if choice == "q":
            return "quit"

        if choice == "f":
            region, method = fixed_trim_region(df), "fixed_trim"

        elif choice == "t":
            try:
                use_tol_fz = float(input(f"  Fz tolerance as fraction (now {use_tol_fz}): ") or use_tol_fz)
                use_tol_ff = float(input(f"  Ff tolerance as fraction (now {use_tol_ff}): ") or use_tol_ff)
                win_s = float(input(f"  window seconds (now {win_s}): ") or win_s)
                min_s = float(input(f"  minimum steady seconds (now {min_s}): ") or min_s)
            except ValueError:
                print("  invalid number, keeping previous values.")
                continue
            new_region = find_steady_region(df, use_tol_fz, use_tol_ff, win_s, min_s)
            if new_region is None:
                print("  no steady region found with those settings; keeping previous window.")
            else:
                region, method = new_region, "auto"

        elif choice == "m":
            try:
                t0 = float(input("  start time: "))
                t1 = float(input("  end time: "))
            except ValueError:
                print("  invalid number.")
                continue
            region, method = region_from_times(df, t0, t1), "manual"

        else:
            print("  unrecognised option.")

    

def read_extracted(path):
    """read a csv whose metadata sits above the real header row.F
    Finds the first line containing T, Fz, and Ff column names and uses it as a header and drops unit and blank rows below. """
    
    wanted = {time_col, Fz_col, Ff_col}
    
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        lines = fh.readlines()
        
    header_idxs = [
        i for i, line in enumerate(lines)
        if wanted.issubset({x.strip() for x in line.split(",")})]
    
    if not header_idxs:
        raise ValueError(f"Could not find a header row containing {sorted(wanted)} in {Path(path).name}")
      
    blocks = []
    for n, start in enumerate(header_idxs):
        end = header_idxs[n+1] if n + 1 < len(header_idxs) else len(lines)
        
        rows = list(csv.reader(lines[start:end]))
        header = [h.strip() for h in rows[0]]
        width = len(header)

        # pad/trim each row to the header width so metadata lines can't break parsing
        body = [(r + [""] * width)[:width] for r in rows[1:]]
        block = pd.DataFrame(body, columns=header)

        # units row, blank row and trailing metadata are non-numeric, so they become NaN and are dropped
        key_cols = [time_col, Fz_col, Ff_col]
        block[key_cols] = block[key_cols].apply(pd.to_numeric, errors="coerce")
        block = block.dropna(subset=key_cols).reset_index(drop=True)

        if not block.empty:
            if is_cycle:
                block[is_cycle] = n + 1
            blocks.append(block)

    if not blocks:
        raise ValueError(f"No numeric data found in {Path(path).name}")

    return pd.concat(blocks, ignore_index=True)
    
def main():
    
    global summary_file
    
    parser = argparse.ArgumentParser(description = "Find steady-state regions, confirm them visually, and save averages.")
    
    parser.add_argument("files", nargs="*", type = Path, help = "path to a .csv file(s)")
    
    parser.add_argument("-f", "--folder", type = Path, default=input_folder, help=f"folder of extracted .csv files (default: {input_folder})")
    
    parser.add_argument("-o", "--output", type = Path, default=summary_file, help=f"summary csv to write to (default{summary_file})")
    
    parser.add_argument("--grouping", default="*.csv", help="global grouping within the folder to target eg. '*tool3_*.csv'")
    
    parser.add_argument("-r", "--redo", action="store_true", help="re-review files already in the summary file")
    
    args=parser.parse_args()
    
    
    summary_file = args.output
    
    if args.files:
        files = args.files
    else:
        files = sorted(args.folder.glob(args.grouping))
    
    missing = [f for f in files if not f.exists()]
    if missing:
        print("File(s) not found:", *missing, sep="\n ")
        return
    if not files:
        print(f"No files matching '{args.grouping}' in {args.folder.resolve()}")
        return
    
    done= set()
    if not args.redo and summary_file.exists():
        done = set(pd.read_csv(summary_file)["file"])
        
    plt.ion()
    for f in files:
        if f.name in done:
            print(f"Skipping {f.name} as it is already in {summary_file}, us --redo to review again")
            continue
        
        df = read_extracted(f)
        
        if is_cycle and is_cycle in df.columns:
            for cyc, g in df.groupby(is_cycle):
                result = review_segment(g.reset_index(drop=True), f, f"{f.name} cycle{cyc}", cyc)
                if result == "quit":
                    return
                
        else:
            if review_segment(df, f, f.name) =="quit":
                return
    
    print(f"\nDone. Summary saved in {summary_file.resolve()}")
        

if __name__ == "__main__":
    main()


 
    