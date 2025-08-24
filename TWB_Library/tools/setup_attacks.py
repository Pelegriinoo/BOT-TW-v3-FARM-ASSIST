#!/usr/bin/env python3
"""
TWB Web Attack Interface Setup Tool
Initial configuration utility for web interface
Location: tools/setup_attacks.py - Setup and configuration utilities
"""

import json
import os
import sys
import logging
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_interface():
    """Initialize web attack interface configuration"""
    logger.info("Starting TWB Web Attack Interface setup")
    
    # Change to parent directory for file operations
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    os.chdir(parent_dir)
    
    # Create attacks.json if it doesn't exist
    if not os.path.exists("attacks.json"):
        create_example_attacks()
    else:
        logger.info("attacks.json already exists, skipping creation")
    
    # Create cache directory structure
    try:
        os.makedirs("cache/hunter", exist_ok=True)
        os.makedirs("webmanager/attacks", exist_ok=True)
        logger.info("Directory structure verified")
    except OSError as e:
        logger.error("Failed to create directory structure: %s", e)
        return False
    
    logger.info("Setup completed successfully")
    logger.info("Configuration file: attacks.json")
    logger.info("Web interface available at: http://127.0.0.1:5000/attacks")
    logger.info("Start server with: python -m webmanager.server")
    return True

def create_example_attacks():
    """Create basic attacks.json file with example data"""
    logger.info("Creating example attacks.json file")
    
    tomorrow = datetime.now() + timedelta(days=1)
    
    data = {
        "info": {
            "created": datetime.now().strftime("%d/%m/%Y"),
            "description": "Attacks created via Web Interface TWB",
            "version": "2.0"
        },
        "attacks": [
            {
                "id": "example_farm",
                "source_village": "YOUR_VILLAGE_ID",
                "target_coordinates": [500, 500],
                "arrival_time": f"{tomorrow.strftime('%d/%m/%Y')} 20:00:00",
                "troops": {"axe": 3000, "light": 1500},
                "type": "farm",
                "enabled": False,
                "notes": "Example attack - Configure your villages and enable!"
            },
            {
                "id": "example_support",
                "source_village": "YOUR_VILLAGE_ID",
                "target_coordinates": [501, 501],
                "arrival_time": f"{tomorrow.strftime('%d/%m/%Y')} 21:00:00",
                "troops": {"spear": 5000, "sword": 3000},
                "type": "support",
                "enabled": False,
                "notes": "Example support - Configure villages and coordinates!"
            }
        ]
    }
    
    try:
        with open("attacks.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("attacks.json created with example attack and support configurations")
        return True
    except IOError as e:
        logger.error("Failed to create attacks.json: %s", e)
        return False

def reset_configuration():
    """Reset attack configuration to defaults"""
    logger.info("Resetting attack configuration")
    
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    os.chdir(parent_dir)
    
    # Backup existing config
    if os.path.exists("attacks.json"):
        backup_name = f"attacks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.rename("attacks.json", backup_name)
        logger.info(f"Existing configuration backed up to: {backup_name}")
    
    # Create fresh config
    return create_example_attacks()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='TWB Attack Interface Setup Tool')
    parser.add_argument('--reset', action='store_true', help='Reset configuration to defaults')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        if args.reset:
            success = reset_configuration()
        else:
            success = setup_interface()
            
        if success:
            logger.info("Setup process completed successfully")
        else:
            logger.error("Setup process failed")
            exit(1)
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        exit(0)
    except Exception as e:
        logger.error("Unexpected error during setup: %s", e)
        exit(1)
