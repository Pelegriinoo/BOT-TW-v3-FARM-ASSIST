#!/usr/bin/env python3
"""
TWB Attack Scheduler - Web Interface Integration
Attack scheduling system for web interface integration
Location: webmanager/attacks/scheduler.py - Attack scheduling component
"""

import json
import sys
import os
import time
import logging
from datetime import datetime, timedelta

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from game.hunter import Hunter
from core.filemanager import FileManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TWBAttackScheduler:
    """Attack scheduler for TWB web interface integration"""
    
    def __init__(self, json_file=None):
        if json_file is None:
            # Default to project root attacks.json
            json_file = os.path.join(project_root, "attacks.json")
        
        self.json_file = json_file
        self.hunter = Hunter()
        self.scheduled_attacks = {}
        self.logger = logging.getLogger(f"{__name__}.TWBAttackScheduler")
        
    def load_attacks_from_json(self):
        """Load attacks from JSON file"""
        self.logger.info("Loading attacks from: %s", self.json_file)
        
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            attacks = data.get("attacks", [])
            self.logger.info("Found %d attacks in JSON", len(attacks))
            return attacks
            
        except FileNotFoundError:
            self.logger.error("File %s not found!", self.json_file)
            return []
            
        except json.JSONDecodeError as e:
            self.logger.error("JSON error: %s", e)
            return []
    
    def parse_arrival_time(self, time_str):
        """Convert time string to timestamp with multiple format support"""
        original_time = time_str
        
        # Support for "today HH:MM:SS" and "hoje HH:MM:SS"
        if time_str.startswith(("today ", "hoje ")):
            time_part = time_str.replace("today ", "").replace("hoje ", "")
            today = datetime.now().strftime("%d/%m/%Y")
            time_str = f"{today} {time_part}"
        
        # Support for "tomorrow HH:MM:SS" and "amanhã HH:MM:SS"
        elif time_str.startswith(("tomorrow ", "amanhã ")):
            time_part = time_str.replace("tomorrow ", "").replace("amanhã ", "")
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
            time_str = f"{tomorrow} {time_part}"
        
        # Convert to timestamp
        try:
            dt = datetime.strptime(time_str, "%d/%m/%Y %H:%M:%S")
            timestamp = dt.timestamp()
            
            self.logger.debug("Time conversion: '%s' -> %s (timestamp: %.0f)", 
                            original_time, dt.strftime('%d/%m/%Y %H:%M:%S'), timestamp)
            return timestamp
            
        except ValueError as e:
            self.logger.error("Invalid time format: %s - %s", time_str, e)
            return None
    
    def validate_attack(self, attack):
        """Validate attack data structure and requirements"""
        attack_id = attack.get("id", "no_id")
        
        # Required fields
        required_fields = ["source_village", "arrival_time", "troops"]
        for field in required_fields:
            if field not in attack:
                self.logger.error("Attack %s: Missing required field: %s", attack_id, field)
                return False
        
        # Must have coordinates OR village_id
        if not attack.get("target_coordinates") and not attack.get("target_village_id"):
            self.logger.error("Attack %s: Must specify target_coordinates OR target_village_id", attack_id)
            return False
        
        # Validate troops
        troops = attack.get("troops", {})
        if not troops or not isinstance(troops, dict):
            self.logger.error("Attack %s: Invalid troops data", attack_id)
            return False
        
        # At least 1 troop
        if not any(int(amount) > 0 for amount in troops.values()):
            self.logger.error("Attack %s: Must have at least 1 troop", attack_id)
            return False
        
        return True
    
    def schedule_attacks(self):
        """Schedule all valid attacks from JSON file"""
        self.logger.info("Starting attack scheduling")
        
        attacks = self.load_attacks_from_json()
        
        if not attacks:
            self.logger.info("No attacks found in JSON")
            return 0
        
        scheduled_count = 0
        skipped_count = 0
        
        for attack in attacks:
            attack_id = attack.get("id", f"attack_{len(self.scheduled_attacks)}")
            self.logger.info("Processing attack: %s", attack_id)
            
            # Skip disabled attacks
            if not attack.get("enabled", True):
                self.logger.info("Attack %s: Disabled, skipping", attack_id)
                skipped_count += 1
                continue
            
            # Validate attack
            if not self.validate_attack(attack):
                self.logger.warning("Attack %s: Invalid data, skipping", attack_id)
                skipped_count += 1
                continue
            
            # Convert arrival time
            arrival_timestamp = self.parse_arrival_time(attack["arrival_time"])
            if not arrival_timestamp:
                self.logger.warning("Attack %s: Invalid arrival time, skipping", attack_id)
                skipped_count += 1
                continue
            
            # Check if not in the past
            if arrival_timestamp < time.time():
                arrival_dt = datetime.fromtimestamp(arrival_timestamp)
                self.logger.warning("Attack %s: Scheduled for past time (%s), skipping", 
                                  attack_id, arrival_dt.strftime('%d/%m/%Y %H:%M:%S'))
                skipped_count += 1
                continue
            
            # Schedule in Hunter
            if arrival_timestamp not in self.hunter.schedule:
                self.hunter.schedule[arrival_timestamp] = []
            
            attack_data = {
                "id": attack_id,
                "source": attack["source_village"],
                "target": attack.get("target_village_id"),
                "target_coords": attack.get("target_coordinates"),
                "troops": attack["troops"],
                "type": attack.get("type", "attack"),
                "notes": attack.get("notes", "")
            }
            
            self.hunter.schedule[arrival_timestamp].append(attack_data)
            self.scheduled_attacks[attack_id] = attack_data
            
            scheduled_count += 1
            arrival_dt = datetime.fromtimestamp(arrival_timestamp)
            
            self.logger.info("Attack %s: Scheduled successfully", attack_id)
            self.logger.info("  Target: %s", attack.get('target_village_id', attack.get('target_coordinates')))
            self.logger.info("  Arrival: %s", arrival_dt.strftime('%d/%m/%Y %H:%M:%S'))
            self.logger.info("  Troops: %s", attack['troops'])
            if attack.get("notes"):
                self.logger.info("  Notes: %s", attack['notes'])
        
        self.logger.info("Scheduling summary - Scheduled: %d, Skipped: %d, Total: %d", 
                        scheduled_count, skipped_count, len(attacks))
        
        if scheduled_count > 0:
            self.save_hunter_state()
            self.logger.info("State saved to: cache/hunter/")
        
        return scheduled_count
    
    def save_hunter_state(self):
        """Save Hunter state to cache directory"""
        cache_dir = os.path.join(project_root, "cache", "hunter")
        os.makedirs(cache_dir, exist_ok=True)
        
        hunter_data = {
            "scheduled_attacks": self.scheduled_attacks,
            "hunter_schedule": {},
            "last_update": datetime.now().isoformat(),
            "total_attacks": len(self.scheduled_attacks)
        }
        
        # Convert timestamps to strings (JSON serializable)
        for timestamp, attacks in self.hunter.schedule.items():
            hunter_data["hunter_schedule"][str(timestamp)] = attacks
        
        # Save to cache
        cache_file = os.path.join(cache_dir, "scheduled_attacks.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(hunter_data, f, indent=4, ensure_ascii=False)
            
            self.logger.info("State saved to: %s", cache_file)
        except IOError as e:
            self.logger.error("Failed to save state: %s", e)
    
    def list_scheduled_attacks(self):
        """List all scheduled attacks with timing information"""
        if not self.hunter.schedule:
            self.logger.info("No attacks scheduled in Hunter")
            return
        
        self.logger.info("Scheduled attacks in Hunter:")
        
        total_attacks = 0
        
        for timestamp, attacks in sorted(self.hunter.schedule.items()):
            arrival_dt = datetime.fromtimestamp(timestamp)
            time_until = timestamp - time.time()
            
            if time_until > 0:
                hours = int(time_until // 3600)
                minutes = int((time_until % 3600) // 60)
                seconds = int(time_until % 60)
                time_str = f"in {hours}h {minutes}m {seconds}s"
            else:
                time_str = "PAST"
            
            self.logger.info("%s (%s)", arrival_dt.strftime('%d/%m/%Y %H:%M:%S'), time_str)
            
            for attack in attacks:
                total_attacks += 1
                self.logger.info("  ID: %s", attack.get('id', 'no_id'))
                self.logger.info("  Source: %s", attack.get('source'))
                self.logger.info("  Target: %s", attack.get('target', attack.get('target_coords')))
                self.logger.info("  Troops: %s", attack.get('troops'))
                self.logger.info("  Type: %s", attack.get('type', 'attack'))
                if attack.get("notes"):
                    self.logger.info("  Notes: %s", attack.get('notes'))
        
        self.logger.info("Total scheduled attacks: %d", total_attacks)

def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="TWB Attack Scheduler - Web Interface Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python scheduler.py --schedule           # Schedule attacks from JSON
  python scheduler.py --list              # List scheduled attacks  
  python scheduler.py --file custom.json -s # Use custom file
        """
    )
    
    parser.add_argument("--file", "-f", default=None, 
                       help="JSON attacks file (default: project_root/attacks.json)")
    parser.add_argument("--schedule", "-s", action="store_true", 
                       help="Schedule attacks from JSON")
    parser.add_argument("--list", "-l", action="store_true", 
                       help="List scheduled attacks")
    
    args = parser.parse_args()
    
    print("TWB ATTACK SCHEDULER - Web Interface Integration")
    print(f"File: {args.file or 'project_root/attacks.json'}")
    print("-" * 50)
    
    scheduler = TWBAttackScheduler(args.file)
    
    if args.schedule:
        count = scheduler.schedule_attacks()
        if count > 0:
            print(f"\nSuccess: {count} attacks scheduled!")
            print("Start TWB bot to execute the attacks")
        else:
            print("\nWarning: No attacks were scheduled")
            
    elif args.list:
        scheduler.list_scheduled_attacks()
        
    else:
        print("Usage:")
        print(f"  python {os.path.basename(__file__)} --schedule    # Schedule attacks")
        print(f"  python {os.path.basename(__file__)} --list       # List scheduled")
        print(f"  python {os.path.basename(__file__)} --help       # Full help")

if __name__ == "__main__":
    main()
