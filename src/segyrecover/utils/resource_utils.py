"""Utility functions for handling resources."""
import os
import shutil
import importlib.resources

def copy_tutorial_files(base_dir):
    """
    Copy tutorial files to the specified directory.
    
    Args:
        base_dir (str): Target directory where tutorial files will be copied
    """
    print(f"Copying tutorial files to {base_dir}")
    
    # Create the target directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    try:
        # Get the path to the examples directory
        with importlib.resources.path('segyrecover', 'examples') as tutorial_path:
            tutorial_dir = str(tutorial_path)
        
        if os.path.exists(tutorial_dir):
            for folder in ["GEOMETRY", "IMAGES", "PARAMETERS"]:
                src_folder = os.path.join(tutorial_dir, folder)
                dst_folder = os.path.join(base_dir, folder)
                
                if os.path.exists(src_folder):
                    # Create destination folder if it doesn't exist
                    os.makedirs(dst_folder, exist_ok=True)
                    
                    # Copy files from source folder to destination folder
                    for file in os.listdir(src_folder):
                        src_path = os.path.join(src_folder, file)
                        dst_path = os.path.join(dst_folder, file)
                        if os.path.isfile(src_path):
                            shutil.copy2(src_path, dst_path)
            print(f"Tutorial files copied successfully from {tutorial_dir}")
        else:
            print(f"Tutorial directory not found: {tutorial_dir}")
    except Exception as e:
        print(f"Error copying tutorial files: {e}")