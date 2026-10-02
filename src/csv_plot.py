# -*- coding: utf-8 -*-
"""
Created on Fri Oct  2 09:06:04 2026

@author: map25bg

This code is designed to take a .csv file (from csv_extract.py) and plot it. In three different ways:
    single variable plot
    two variable plot
    multiple cycles plot (requires a folder as input)
    
Run file in CLI by 
%run csv_plot "file_path_or_folder_path_of_data" --mode one_variable or two_variable or cycles --x_col "Y" --y_col "Fz" 

default values for x_col = Y and y_col = COF

Google Gemini Gen AI was used to complete this code 
"""

import io
import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse
import glob
import re

def load_extracted_csv(filepath):
    """loading in the extracted UMT steps, skip the metadata and return a dataframe"""
    
    with open(filepath, "r") as f:
        lines = f.readlines()
        
        #look through lines in the .csv the first line that starts with "T" will be listed as the header line
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("T,Fx"):
            header_idx = i
            break
    if header_idx is None:
        return None
        
    clean_data = [lines[header_idx]] #create a list of the clean data, starting with just the column headings
    for line in lines[header_idx + 1 :]:
        if line.startswith("sec") or not line.strip(): #keep going and don't store if the line starts with "sec" and strip any blank lines - so it doesn't return an error when trying to collect the following digits
            continue
        if line[0].isdigit():
            clean_data.append(line)
    
    csv_data = "".join(clean_data)
    return pd.read_csv(io.StringIO(csv_data))


def plot_one_variable(file_paths, x_col, y_col):
    """plotting just one variable"""
    for path in file_paths:
        df = load_extracted_csv(path)
        if df is None or y_col not in df.columns:
            print(f"Skipping {path}: Missing the required colummns ({y_col})")
            continue

        #setup figure
        fig, data = plt.subplots(figsize=(10,6))

        filename = os.path.basename(path)
        
        #plot data 
        data.plot(
            df[x_col], df[y_col], color="tab:blue", label=f"{y_col}")
        
        #labels
        data.set_xlabel(f"{x_col} (Displacement, mm)") ## This needs to be changed depending on inputs
        data.set_ylabel(f"{y_col}")               ## so does this please don't forget or you will fuck up you plots
        
        data.legend(loc = "upper right")
        
        plt.title(f"Plot of {y_col} for {filename}")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        
def plot_two_variables(file_paths, x_col="Y", col1 = "COF", col2 = "Ff"):
    """plotting col1 and col2 on two separate y axes but with the same axis values for easy comparison"""
    for path in file_paths:
        df = load_extracted_csv(path)
        if df is None or col1 not in df.columns or col2 not in df.columns:
            print(f"Skipping {path}: Missing the required colummns ({col1}, {col2})")
            continue
        
        #setup figure
        fig, ax1 = plt.subplots(figsize=(10,6))
        ax2 = ax1.twinx()
        
        filename = os.path.basename(path)
        
        #plot data 
        line1 = ax1.plot(
            df[x_col], df[col1], color="tab:blue", label=f"{col1}")
        line2 = ax2.plot(
            df[x_col], df[col2], color="tab:red", label=f"{col2}")
        
        #make it so that the axes have the same limits
        y_min = min(df[col1].min(), df[col2].min())
        y_max = max(df[col1].max(), df[col2].max())
        
        if y_max != y_min:
            margin = (y_max - y_min) * 0.05
        else:
            margin = 1.0
            
            
        ax1.set_ylim(y_min - margin, y_max + margin)
        ax2.set_ylim(y_min - margin, y_max + margin)
        
        #labels
        ax1.set_xlabel(f"{x_col} (Displacement, mm)")
        ax1.set_ylabel(col1)
        ax2.set_ylabel(col2)
        
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc="upper right")
        
        plt.title(f"Plot of {col1} and {col2} for {filename}")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        
def plot_multiple_cycles(file_paths, x_col="Y", y_col="COF"):
    """overlays plots from multiple files into a single plot"""
    
    fig, ax = plt.subplots(figsize=(10,6))
    files_plotted=0
    
    def extract_cycle(path):
        filename = os.path.basename(path)
        match = re.search(r'(\d{3})', filename)
        return int(match.group(1)) if match else filename
    
    sorted_paths = sorted(file_paths, key = extract_cycle)
    
    for path in sorted_paths:
        df = load_extracted_csv(path)
        if df is None or x_col not in df.columns or y_col not in df.columns:
            print(f"Skipping {path}: Missing the required columns ({x_col}, {y_col})")
            continue
        
        filename = os.path.basename(path)
        #extract the cycle number (3-digits)
        match = re.search(r'(\d{3})', filename)
        if match:
            label_name = f"Cycle {match.group(1)}"
        else:
            label_name = filename
        
        ax.plot(df[x_col], df[y_col], label = label_name)
        files_plotted = files_plotted + 1
        
    if files_plotted == 0:
        print("No valid data files found")
        plt.close(fig)
        return
    
    ax.set_xlabel(f"{x_col} (Displacement, mm)") #change this if x axis is not displacement
    ax.set_ylabel(f"{y_col}") # add units here if not using COF
    ax.set_title(f"Plot of {y_col} for all cycles of {filename}")
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1.0))
    ax.grid(True)
    plt.tight_layout()
    plt.show()
    
    

def main():
    parser = argparse.ArgumentParser(description = "Plot extracted UMT data files.")
    
    parser.add_argument("input_path", type = str, help = "path to either a .csv file or a folder containing .csv files")
    
    parser.add_argument("--mode", choices=["one_variable", "two_variables", "cycles"], default="one_variable", 
                        help = "Choose either 'one_variable', 'two_variables' or 'cycles' to plot")
    
    parser.add_argument("--x_col", type = str, default="Y", help = "Column selection for x-axis (default: Y, Displacement (mm)")

    parser.add_argument("--y_col", type = str, default = "COF", help = "Column selection for y-axis (default: COF")    
    
    args = parser.parse_args()
    
    #see if it is a single file or a folder
    if os.path.isfile(args.input_path):
        file_paths = [args.input_path]
        
    else:
        os.path.isdir(args.input_path)
        file_paths = glob.glob(os.path.join(args.input_path, "*.csv"))
        
    if not file_paths:
        print(f"No CSV files found matching: {args.input_path}")
        return
    if args.mode == "one_variable":
        plot_one_variable(file_paths, x_col=args.x_col, y_col=args.y_col)
    elif args.mode == "two_variables":
        plot_two_variables(file_paths, x_col=args.x_col, col1 = "COF", col2 = "Ff")
    else:
        plot_multiple_cycles(file_paths, x_col=args.x_col, y_col=args.y_col)
                 
            
    
if __name__ == "__main__":
    main()