import os

# Set the path to the directory shown in your screenshots. 
# Update the drive letter (e.g., 'C:') to match your local machine.
directory_path = r"C:\Users\smitt\Jen_project\sagehen_meadows\results\plots\ET\White_Van_Gun"

# Iterate through all files in the target directory
for filename in os.listdir(directory_path):
    # Check if 'Smoothed' is in the current file's name
    if "Smoothed" in filename:
        # Generate the new file name
        new_filename = filename.replace("Smoothed", "no_delay")
        
        # Construct the full absolute paths for renaming
        old_filepath = os.path.join(directory_path, filename)
        new_filepath = os.path.join(directory_path, new_filename)
        
        # Rename the file
        os.rename(old_filepath, new_filepath)
        print(f"Renamed: '{filename}' -> '{new_filename}'")