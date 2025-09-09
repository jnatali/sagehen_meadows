import os
import glob
import pandas as pd

# --- Configuration ---
# Define the relative paths from the script's location in 'scripts/'
RAW_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW')
PROCESSED_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')
PROCESSED_CSV_FILENAME = 'processed_canopy_temp.csv'

def main():
    """
    Main function to run the data processing workflow.
    """
    # Create the full path for the output file
    processed_csv_path = os.path.join(PROCESSED_DATA_DIR, PROCESSED_CSV_FILENAME)

    print("--- Starting IRR Data Processing ---")

    # 1. Load any existing processed data into a dataframe
    print(f"Checking for existing data at: {processed_csv_path}")
    if os.path.exists(processed_csv_path):
        existing_df = pd.read_csv(processed_csv_path)
        print(f"Loaded {len(existing_df)} existing records.")
    else:
        # If no file exists, start with an empty DataFrame
        existing_df = pd.DataFrame()
        print("No existing data file found. A new one will be created.")

    # 2. Find all raw data files
    #Points to RAW_DATA_DIR directory with file names Data Log * is a wildcard for any characters after that
    search_pattern = os.path.join(RAW_DATA_DIR, 'Data Log*.txt') 
    #glob.glob finds all files matching the search pattern and returns them as a list named all_raw_files
    all_raw_files = glob.glob(search_pattern)

    # 3. Determine which files are new and need to be processed
    # Check if 'source_file' column exists to track processed files
    # If it does, create a set of processed file names
    if 'source_file' in existing_df.columns:
        processed_files = set(existing_df['source_file'])
    else:
    #if not, create an empty set
        processed_files = set()

    #processed_files is a collection of all the filenames the script has already processed

    # The for loop version for understandability
    new_files_to_process = []  # 1. Start with an empty list

    for f in all_raw_files:  # 2. Loop through every file path found by glob
        
        # 3. Get just the filename from the full path
        filename = os.path.basename(f)
        
        # 4. Check if this filename is NOT in our set of already processed files
        if filename not in processed_files:
            
            # 5. If it's a new file, add its full path to our "to-do" list
            new_files_to_process.append(f)

    # 4. If there are no new files, exit 
    if not new_files_to_process:
        print("\nNo new data files to process. Your data is already up-to-date.")
        print("--- Processing Complete ---")
        exit(0)

    # 5. Process the new files
    print(f"\nFound {len(new_files_to_process)} new files to process:")

    #Create an empty list to hold dataframes for each new file
    new_data_frames = []
    for file_path in new_files_to_process:
        filename = os.path.basename(file_path)
        print(f" - Reading '{filename}'...")
        try:
            # Read the semicolon seperated data file into a temporary dataframe
            temp_df = pd.read_csv(file_path, sep=';')
            
            # Add the source_file column to track where the data came from
            temp_df['source_file'] = filename
            new_data_frames.append(temp_df)
        except Exception as e:
            print(f"   - Warning: Could not process file {filename}. Error: {e}")

    # 6. Combine the new data and append it to the existing data
    if new_data_frames:
        new_data_df = pd.concat(new_data_frames, ignore_index=True)
        
        # Combine the old and new dataframes
        updated_df = pd.concat([existing_df, new_data_df], ignore_index=True)
        
        # 7. Save the updated dataframe back to the CSV file
        # Use index=False to avoid writing an extra column for the row numbers
        os.makedirs(PROCESSED_DATA_DIR, exist_ok=True) # Ensure directory exists
        updated_df.to_csv(processed_csv_path, index=False)
        
        print(f"\nSuccessfully added {len(new_data_df)} new records.")
        print(f"Total records are now {len(updated_df)}.")
        print(f"Updated data saved to: {processed_csv_path}")
    
    print("--- Processing Complete ---")


if __name__ == "__main__":
    main()
