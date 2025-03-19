import os
import numpy as np
import matplotlib.pyplot as plt

def display_npy_files(raw_folder):
    """Display .npy files in the specified folder in a 2x2 grid."""
    npy_files = [f for f in os.listdir(raw_folder) if f.endswith('.npy')]
    
    # Sort files by their processing step number
    npy_files.sort(key=lambda x: int(x.split('_')[0].replace('step', '')))
    
    if len(npy_files) > 0:
        # Create a figure with 2x2 subplots
        fig, axs = plt.subplots(2, 2, figsize=(16, 12))
        axs = axs.flatten()
        
        # Load and display each .npy file
        for i, npy_file in enumerate(npy_files[:4]):  # Limit to first 4 files
            file_path = os.path.join(raw_folder, npy_file)
            data = np.load(file_path)
            
            # Create a normalized version for better visualization
            vmax = np.max(np.abs(data))
            vmin = -vmax
            
            # Display the data
            im = axs[i].imshow(data, aspect='auto', cmap='seismic', 
                         interpolation='none', vmin=vmin, vmax=vmax)
            
            # Add a colorbar
            cbar = plt.colorbar(im, ax=axs[i])
            cbar.set_label('Amplitude')
            
            # Add title and labels
            axs[i].set_title(f"{npy_file}")
            axs[i].set_xlabel('Trace')
            axs[i].set_ylabel('Sample')
        
        plt.tight_layout()
        plt.show()
    else:
        print("No .npy files found in the specified folder.")

if __name__ == "__main__":
    raw_folder = r'C:\Users\Alex\Documents\SEGYRecover\raw_data'
    if not os.path.exists(raw_folder):
        print(f"Folder '{raw_folder}' does not exist.")
    else:
        display_npy_files(raw_folder)