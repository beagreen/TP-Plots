# -*- coding: utf-8 -*-
"""
Created on Wed Sep 30 13:19:26 2026

@author: map25bg

This is written to take .csv files from the UMT. Find the second step and save that as a .csv, stripping the rest of the data.
It is written with the Trial Packages in mind

Google Gemini Gen AI was used to complete this code 
"""

import glob
import os
import argparse

def process_and_save_umt_csv(filepath, output_folder = "extracted_steps"):
    """Reading in a .csv file, extracting Step 2 and every third step after (the 'action' steps in Trial Packages) 
    and saving the output as a new .csv file"""
    
    #catch if CLI input filepath is invalid
    if not os.path.exists(filepath):
        print(f"Error: File not found -> {filepath}")
        return
    
    #Read the file line by line
    with open (filepath, "r") as f:     
        lines = f.readlines()
       
        #Extract the file metadata
        metadata_lines = []              
        metadata_end_idx = None
        
        for idx, line in enumerate(lines):
            if line.startswith("Step No."):
                metadata_end_idx = idx
                break
            metadata_lines.append(line)
            
        if metadata_end_idx is None:
            print(f"Skipping {filepath}: No Steps found in file.")
            return

    #Extract the data from the 'action' steps (eg. 2, 5, 8 etc.) and group by each step
    steps = {}
    
    current_step = None
    step_lines = []
    
    for line in lines[metadata_end_idx:]: #starting at the end of the metadata and reading each step in 
        if line.startswith("Step No."): #beginning of loop used for all steps
            if current_step is not None:
                steps[current_step] = step_lines #if current_step has a value save the list of lines (step_lines)
            current_step = int(line.split("Step No.")[1].strip()) #take the step no. from the .csv as the current_step
            step_lines = [line] #include Step No.# as a header
        elif current_step is not None: #curent line does not start with Step No.#, still append this data eg. column headers
            step_lines.append(line)
            
     # Loop ends - save what is left in step_lines
    if current_step is not None:
        steps[current_step] = step_lines
     
    #filter for only the 'action' steps (2, 5, 8, . . )
    action_lines_step_number = [s for s in steps.keys() if (s-2) % 3 == 0]
    
    if not action_lines_step_number:
        print(f"No target steps (2, 5, 8, . . . ) found in {filepath}")
        return
    
    #Assemble the new file (metadata + selected steps)
    new_file_content = list(metadata_lines)
    for step_num in action_lines_step_number:
        new_file_content.extend(steps[step_num])
        
    #save new file
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.basename(filepath)
    output_path = os.path.join(output_folder, f"extracted_{base_name}")
    
    with open(output_path, "w") as f:
        f.writelines(new_file_content)
    
    print(f"saved: {output_path} (Included Steps: {action_lines_step_number})") 
   
   
    
def main():
    parser = argparse.ArgumentParser()
    
    
    parser.add_argument("input_path", type = str,  help = "Path to a .csv file or a foder ontainting .csv files")

    parser.add_argument("-o", "--output", type = str, default = "extracted_steps", help = "Output folder to save files to (default: extracted_steps)")
    
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
    
    for path in file_paths:
        process_and_save_umt_csv(path, output_folder=args.output)
        
if __name__ == "__main__":
    main()    