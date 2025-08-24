import time
import logging
from datetime import datetime

from core.extractors import Extractor
from game.simulator import Simulator


class Hunter:
    game_map = None
    schedule = {}
    target_villages = {}
    villages = []
    sim = Simulator()

    wrapper = None
    targets = {}
    # start timing 2m before attack start
    window = 120
    logger = logging.getLogger("Hunter")

    def nearing_schedule_window(self):
        """
        Check if we are near the sending window
        Now considering that the scheduled time is ARRIVAL time
        """
        current_time = time.time()
        for arrival_time in self.schedule:
            # Activate with enough advance time to calculate duration and wait for sending
            # Maximum attack duration: ~20 minutes (1200s) + 5 minutes margin (300s)
            activation_window = 1500  # 25 minutes before arrival
            time_until_arrival = arrival_time - current_time
            if 0 < time_until_arrival <= activation_window:
                return arrival_time
        return None

    def nearing_window_in_sleep(self, sleep):
        lowest = None
        for item in self.schedule:
            wait = time.time() + sleep
            if item - self.window < wait:
                if not lowest or item < lowest:
                    lowest = item
        return lowest

    def troops_in_village(self, source=None, troops={}):
        if source:
            if self.villages[source].attack.has_troops_available(troops):
                return source
        for v in self.villages:
            if v.attack.has_troops_available(troops):
                return v

    def check_arrival_feasibility(self, source, target, troops, desired_arrival_time):
        """
        Check if it's possible to meet a specific arrival time
        Returns: (feasible, required_send_time, travel_duration)
        """
        current_time = time.time()
        
        # Calculate estimated duration (without preparing the actual attack)
        if isinstance(target, str) and target.startswith("coord_"):
            _, x_str, y_str = target.split("_")
            x, y = int(x_str), int(y_str)
        elif target in self.game_map.map_pos:
            x, y = self.game_map.map_pos[target]
        else:
            return False, 0, 0
        
        # Rough estimate based on distance and troop type
        # (can be refined with more precise calculations)
        source_coords = self.game_map.map_pos.get(source, (0, 0))
        distance = ((x - source_coords[0])**2 + (y - source_coords[1])**2)**0.5
        
        # Estimated speed based on slowest troop
        speed_per_minute = 10  # Conservative estimate
        estimated_duration = max(60, distance * 60 / speed_per_minute)  # Minimum 1 minute
        
        required_send_time = desired_arrival_time - estimated_duration
        
        # Check feasibility
        is_feasible = required_send_time > current_time + 30  # 30s margin
        
        return is_feasible, required_send_time, estimated_duration

    def suggest_earliest_arrival(self, source, target, troops):
        """
        Suggest the earliest possible arrival time
        """
        current_time = time.time()
        _, _, estimated_duration = self.check_arrival_feasibility(source, target, troops, current_time + 3600)
        
        # Add safety margin
        earliest_arrival = current_time + estimated_duration + 60  # +60s margin
        
        return earliest_arrival

    def send_attack_chain(self, source, item, exact_arrival_time=0, min_sleep_amount_millis=100):
        """
        Execute a chain of scheduled attacks
        item = desired ARRIVAL time
        """
        data = self.schedule[item]
        attack_set = []
        
        # Preliminary feasibility check - only block if arrival has already passed
        current_time = time.time()
        
        if exact_arrival_time <= current_time:
            arrival_dt = datetime.fromtimestamp(exact_arrival_time)
            current_dt = datetime.fromtimestamp(current_time)
            
            self.logger.error("ARRIVAL TIME HAS ALREADY PASSED!")
            self.logger.error("   • Desired arrival: %s", arrival_dt.strftime('%H:%M:%S'))
            self.logger.error("   • Now: %s", current_dt.strftime('%H:%M:%S'))
            return False
        
        self.logger.info("Preparing %d attacks for arrival at %s" % (len(data), datetime.fromtimestamp(exact_arrival_time).strftime('%H:%M:%S')))
        
        # Calculate send time based on duration
        send_times = []
        
        for attack in data:
            # Determine target
            target = None
            if attack.get("target"):
                target = attack["target"]
            elif attack.get("target_coords"):
                # Convert coordinates to village_id if necessary
                coords = attack["target_coords"]
                target = f"coord_{coords[0]}_{coords[1]}"
            
            if not target:
                self.logger.error("Target not found for attack: %s", attack.get("id", "no_id"))
                continue
            
            # Prepare attack and get duration
            attack_type = attack.get("type", "attack")
            result = self.attack(source, target, troops=attack.get("troops", {}), attack_type=attack_type)
            
            if result:
                if isinstance(result, tuple):
                    # If returned tuple (data, duration)
                    attack_data, duration = result
                    
                    # Calculate send time: arrival - duration
                    send_time = exact_arrival_time - duration
                    current_time = time.time()
                    
                    # Check if it's still possible to send at the right time
                    if send_time <= current_time:
                        send_dt = datetime.fromtimestamp(send_time)
                        current_dt = datetime.fromtimestamp(current_time)
                        arrival_dt = datetime.fromtimestamp(exact_arrival_time)
                        
                        # Calculate new possible arrival time
                        earliest_arrival = current_time + duration + 30  # +30s margin
                        earliest_arrival_dt = datetime.fromtimestamp(earliest_arrival)
                        
                        self.logger.error("IMPOSSIBLE TO MEET ARRIVAL TIME!")
                        self.logger.error("   • Desired arrival: %s", arrival_dt.strftime('%H:%M:%S'))
                        self.logger.error("   • Required send time: %s (already passed!)", send_dt.strftime('%H:%M:%S'))
                        self.logger.error("   • Now: %s", current_dt.strftime('%H:%M:%S'))
                        self.logger.error("   • Earliest possible arrival: %s", earliest_arrival_dt.strftime('%H:%M:%S'))
                        
                        return False
                    
                    send_times.append(send_time)
                    
                    attack_set.append(attack_data)
                    
                    arrival_dt = datetime.fromtimestamp(exact_arrival_time)
                    send_dt = datetime.fromtimestamp(send_time)
                    
                    self.logger.info("Attack %s: send %s → arrival %s (duration: %ds)", 
                                   attack.get("id", "no_id"),
                                   send_dt.strftime('%H:%M:%S'),
                                   arrival_dt.strftime('%H:%M:%S'),
                                   duration)
                else:
                    # If returned only data
                    attack_set.append(result)
                    send_times.append(exact_arrival_time)  # Fallback
                    self.logger.debug("Attack prepared: %s", attack.get("id", "no_id"))
            else:
                self.logger.error("Failed to prepare attack: %s", attack.get("id", "no_id"))
        
        if not attack_set:
            self.logger.error("No attacks were prepared successfully")
            # Disable priority mode
            self.wrapper.priority_mode = False
            return False
        
        # Use the smallest send time (in case of multiple attacks)
        exact_send_time = min(send_times) if send_times else exact_arrival_time
        
        # Log calculated schedule
        current_time = time.time()
        send_dt = datetime.fromtimestamp(exact_send_time)
        arrival_dt = datetime.fromtimestamp(exact_arrival_time)
        current_dt = datetime.fromtimestamp(current_time)
        wait_time = exact_send_time - current_time
        
        self.logger.info("CALCULATED SCHEDULE:")
        self.logger.info(" • Now: %s", current_dt.strftime('%H:%M:%S'))
        self.logger.info(" • Send: %s (in %.1f minutes)", send_dt.strftime('%H:%M:%S'), wait_time/60)
        self.logger.info(" • Arrival: %s", arrival_dt.strftime('%H:%M:%S'))
        
        # Activate priority mode
        self.wrapper.priority_mode = True
        
        # Wait for exact SEND moment
        if wait_time > 0:
            self.logger.info("Waiting %.1f minutes until send...", wait_time/60)
            
            # For long waits (>1 minute), show progress
            if wait_time > 60:
                last_update = 0
                while time.time() < exact_send_time:
                    time.sleep(1)
                    remaining = exact_send_time - time.time()
                    # Update every 30 seconds
                    if time.time() - last_update > 30:
                        self.logger.info("Still waiting... %.1f minutes remaining", remaining/60)
                        last_update = time.time()
            else:
                # For short waits, just wait
                while time.time() < exact_send_time:
                    time.sleep(0.1)
        
        self.logger.info("SENDING ATTACKS NOW!")
        
        # Execute attacks
        start_time = datetime.now()
        successful_attacks = 0
        
        for prepared_attack in attack_set:
            time.sleep(min_sleep_amount_millis / 1000.0)  # Convert ms to seconds
            result = self.send_attack(source, prepared_attack)
            if result:
                self.logger.info("Attack sent successfully!")
                successful_attacks += 1
            else:
                self.logger.error("Failed to send attack!")
        
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        if successful_attacks > 0:
            self.logger.info("Sent %d attacks in %.0f milliseconds" % (successful_attacks, duration_ms))
            # Disable priority mode
            self.wrapper.priority_mode = False
            return True
        else:
            self.logger.error("No attacks were sent successfully!")
            # Disable priority mode
            self.wrapper.priority_mode = False
            return False

    def attack(self, source, target, troops=None, attack_type="attack"):
        """
        Prepare an attack for sending
        """
        # If target is coordinates, use coordinates
        if isinstance(target, str) and target.startswith("coord_"):
            # Extract coordinates from "coord_x_y" format
            _, x_str, y_str = target.split("_")
            x, y = int(x_str), int(y_str)
            
            # Use correct URL for support
            if attack_type == "support":
                url = f"game.php?village={source}&screen=place&mode=support"
                self.logger.info("Using SUPPORT screen for type '%s'", attack_type)
            else:
                url = f"game.php?village={source}&screen=place"
                self.logger.info("Using ATTACK screen for type '%s'", attack_type)
        else:
            # Target is village_id
            if attack_type == "support":
                url = f"game.php?village={source}&screen=place&mode=support&target={target}"
                self.logger.info("Using SUPPORT screen for village target '%s'", target)
            else:
                url = f"game.php?village={source}&screen=place&target={target}"
                self.logger.info("Using ATTACK screen for village target '%s'", target)
        
        try:
            pre_attack = self.wrapper.get_url(url)
            if not pre_attack:
                self.logger.error("Failed to access attack page")
                return False
            
            pre_data = {}
            for u in Extractor.attack_form(pre_attack):
                if len(u) == 2:
                    k, v = u
                    pre_data[k] = v
            
            if troops:
                self.logger.debug("Received troops: %s", troops)
                # Ensure troops are in correct format
                if isinstance(troops, dict):
                    for unit, amount in troops.items():
                        if amount > 0:  # Only add if amount is greater than 0
                            pre_data[unit] = str(amount)
                            self.logger.debug("Added troop: %s = %d", unit, amount)
                else:
                    self.logger.error("Invalid troop format: %s", type(troops))
            
            # Set coordinates
            if isinstance(target, str) and target.startswith("coord_"):
                _, x_str, y_str = target.split("_")
                x, y = int(x_str), int(y_str)
            elif target in self.game_map.map_pos:
                x, y = self.game_map.map_pos[target]
            else:
                self.logger.error("Target coordinates not found: %s", target)
                return False
            
            post_data = {
                "x": x, 
                "y": y, 
                "target_type": "coord"
            }
            
            # Set correct command based on type
            if attack_type == "support":
                post_data["support"] = "Ondersteunen"  # "Support" button in Dutch
                self.logger.info("Set SUPPORT command")
            else:
                post_data["attack"] = "Aanvallen"  # "Attack" button in Dutch
                self.logger.info("Set ATTACK command")
            
            pre_data.update(post_data)
            
            self.logger.debug("Attack data: %s", pre_data)
            
            # Confirm attack
            confirm_url = f"game.php?village={source}&screen=place&try=confirm"
            conf = self.wrapper.post_url(url=confirm_url, data=pre_data)
            
            if not conf:
                self.logger.error("Failed confirmation request")
                return False
                
            if '<div class="error_box">' in conf.text:
                self.logger.error("Attack confirmation error - page contains error_box")
                # Log specific error for debug
                import re
                error_match = re.search(r'<div class="error_box"[^>]*>(.*?)</div>', conf.text, re.DOTALL)
                if error_match:
                    error_text = error_match.group(1).strip()
                    self.logger.error("Specific error: %s", error_text)
                return False
            
            duration = Extractor.attack_duration(conf)
            
            confirm_data = {}
            for u in Extractor.attack_form(conf):
                if len(u) == 2:
                    k, v = u
                    # For support attacks, keep the support field
                    if k == "support" and attack_type == "support":
                        confirm_data[k] = "1"  # Mark as support
                        self.logger.info("Added 'support' field for attack type '%s'", attack_type)
                    elif k != "support":
                        confirm_data[k] = v
            
            self.logger.info("Prepared data for type '%s': %s", attack_type, confirm_data)
            
            new_data = {
                "building": "main",
                "h": self.wrapper.last_h,
            }
            confirm_data.update(new_data)
            
            if "x" not in confirm_data:
                confirm_data["x"] = x
            if "y" not in confirm_data:
                confirm_data["y"] = y
            
            return confirm_data, duration
            
        except Exception as e:
            self.logger.error("Error preparing attack: %s", str(e))
            return False

    def send_attack(self, source, data):
        return self.wrapper.get_api_action(
            village_id=source,
            action="popup_command",
            params={"screen": "place"},
            data=data,
        )

    def prepare(self, vid, troops=None, attack_type="attack"):
        # Use correct URL for support
        if attack_type == "support":
            url = "game.php?village=%s&screen=place&mode=support&target=%s" % (self.village_id, vid)
            self.logger.info("Using SUPPORT screen for target '%s'", vid)
        else:
            url = "game.php?village=%s&screen=place&target=%s" % (self.village_id, vid)
            self.logger.info("Using ATTACK screen for target '%s'", vid)
        pre_attack = self.wrapper.get_url(url)
        pre_data = {}
        for u in Extractor.attack_form(pre_attack):
            k, v = u
            pre_data[k] = v
        if troops:
            pre_data.update(troops)

        x, y = self.map.map_pos[vid]
        
        # Set correct command based on type
        if attack_type == "support":
            post_data = {"x": x, "y": y, "target_type": "coord", "support": "Ondersteunen"}
            self.logger.info("Set SUPPORT command")
        else:
            post_data = {"x": x, "y": y, "target_type": "coord", "attack": "Aanvallen"}
            self.logger.info("Set ATTACK command")
            
        pre_data.update(post_data)

        confirm_url = "game.php?village=%s&screen=place&try=confirm" % self.village_id
        conf = self.wrapper.post_url(url=confirm_url, data=pre_data)
        if '<div class="error_box">' in conf.text:
            return False
        duration = Extractor.attack_duration(conf)

        confirm_data = {}
        for u in Extractor.attack_form(conf):
            k, v = u
            # For support attacks, keep the support field
            if k == "support" and attack_type == "support":
                confirm_data[k] = "1"  # Mark as support
                self.logger.info("Added 'support' field for attack type '%s' (prepare)", attack_type)
            elif k != "support":
                confirm_data[k] = v
        
        self.logger.info("Prepared data (prepare) for type '%s': %s", attack_type, confirm_data)
        
        new_data = {
            "building": "main",
            "h": self.wrapper.last_h,
        }
        confirm_data.update(new_data)
        if "x" not in confirm_data:
            confirm_data["x"] = x
        result = self.wrapper.get_api_action(
            village_id=self.village_id,
            action="popup_command",
            params={"screen": "place"},
            data=confirm_data,
        )

        return result