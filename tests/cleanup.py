#!/usr/bin/env python
"""
Cleanup script for SEGYRecover application.
Used to remove configuration files during uninstallation.
"""

import os
import shutil
import appdirs

def cleanup_config():
    """Remove all configuration files for SEGYRecover."""
    app_name = "SEGYRecover"
    user_config_dir = appdirs.user_config_dir(app_name)
    
    if os.path.exists(user_config_dir):
        try:
            shutil.rmtree(user_config_dir)
            print(f"Successfully removed configuration directory: {user_config_dir}")
            return True
        except Exception as e:
            print(f"Error removing configuration directory: {str(e)}")
            return False
    else:
        print(f"No configuration directory found at: {user_config_dir}")
        return True

if __name__ == "__main__":
    cleanup_config()