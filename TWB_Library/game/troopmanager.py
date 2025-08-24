"""
Anything that has to do with the recruiting of troops
Auto-unlock scavenge system implemented with correct endpoints
"""
import logging
import math
import random
import time

from core.extractors import Extractor
from game.resources import ResourceManager


class TroopManager:
    """
    Troopmanager class
    """
    can_recruit = True
    can_attack = True
    can_dodge = False
    can_scout = True
    can_farm = True
    can_gather = True
    can_fix_queue = True
    randomize_unit_queue = True

    queue = []
    troops = {}

    total_troops = {}

    _research_wait = 0

    wrapper = None
    village_id = None
    recruit_data = {}
    game_data = {}
    logger = None
    max_batch_size = 50
    wait_for = {}

    _waits = {}

    wanted = {"barracks": {}}

    # Maps troops to the building they are created from
    unit_building = {
        "spear": "barracks",
        "sword": "barracks",
        "axe": "barracks",
        "archer": "barracks",
        "spy": "stable",
        "light": "stable",
        "marcher": "stable",
        "heavy": "stable",
        "ram": "garage",
        "catapult": "garage",
    }

    wanted_levels = {}

    last_gather = 0

    resman = None
    template = None

    def __init__(self, wrapper=None, village_id=None):
        """
        Create the troop manager
        """
        self.wrapper = wrapper
        self.village_id = village_id
        self.wait_for[village_id] = {"barracks": 0, "stable": 0, "garage": 0}
        if not self.resman:
            self.resman = ResourceManager(
                wrapper=self.wrapper, village_id=self.village_id
            )

    def update_totals(self):
        """
        Updates the total amount of recruited units
        """
        main_data = self.wrapper.get_action(
            action="overview", village_id=self.village_id
        )
        self.game_data = Extractor.game_state(main_data)

        if self.resman:
            if "research" in self.resman.requested:
                # new run, remove request
                self.resman.requested["research"] = {}

        if not self.logger:
            village_name = self.game_data["village"]["name"]
            self.logger = logging.getLogger(f"Recruitment: {village_name}")
        self.troops = {}

        get_all = (
                f"game.php?village={self.village_id}&screen=place&mode=units&display=units"
        )
        result_all = self.wrapper.get_url(get_all)

        for u in Extractor.units_in_village(result_all):
            k, v = u
            self.troops[k] = v

        self.logger.debug("Units in village: %s", str(self.troops))

        if not self.can_recruit:
            return

        self.total_troops = {}
        for u in Extractor.units_in_total(result_all):
            k, v = u
            if k in self.total_troops:
                self.total_troops[k] = self.total_troops[k] + int(v)
            else:
                self.total_troops[k] = int(v)
        self.logger.debug("Village units total: %s", str(self.total_troops))

    def start_update(self, building="barracks", disabled_units=[]):
        """
        Starts the unit update for a building
        """
        if self.wait_for[self.village_id][building] > time.time():
            human_ts = self.readable_ts(self.wait_for[self.village_id][building])
            self.logger.info(
                "%s still busy for %s",
                building, human_ts
            )
            return False

        run_selection = list(self.wanted[building].keys())
        if self.randomize_unit_queue:
            random.shuffle(run_selection)

        for wanted in run_selection:
            # Ignore disabled units
            if wanted in disabled_units:
                continue

            if wanted not in self.total_troops:
                if self.recruit(
                        wanted, self.wanted[building][wanted], building=building
                ):
                    return True
                continue

            if self.wanted[building][wanted] > self.total_troops[wanted]:
                if self.recruit(
                        wanted,
                        self.wanted[building][wanted] - self.total_troops[wanted],
                        building=building,
                ):
                    return True

        self.logger.info("Recruitment:%s up-to-date", building)
        return False

    def get_min_possible(self, entry):
        """
        Calculates which units are needed the most
        To get some balance of the total amount
        """
        return min(
            [
                math.floor(self.game_data["village"]["wood"] / entry["wood"]),
                math.floor(self.game_data["village"]["stone"] / entry["stone"]),
                math.floor(self.game_data["village"]["iron"] / entry["iron"]),
                math.floor(
                    (
                            self.game_data["village"]["pop_max"]
                            - self.game_data["village"]["pop"]
                    )
                    / entry["pop"]
                ),
            ]
        )

    def get_template_action(self, levels):
        """
        Read data from templates and determine the troops based op building progression
        """
        last = None
        wanted_upgrades = {}
        for x in self.template:
            if x["building"] not in levels:
                return last

            if x["level"] > levels[x["building"]]:
                return last

            last = x
            if "upgrades" in x:
                for unit in x["upgrades"]:
                    if (
                            unit not in wanted_upgrades
                            or x["upgrades"][unit] > wanted_upgrades[unit]
                    ):
                        wanted_upgrades[unit] = x["upgrades"][unit]

            self.wanted_levels = wanted_upgrades
        return last

    def research_time(self, time_str):
        """
        Calculates unit research time
        """
        parts = [int(x) for x in time_str.split(":")]
        return parts[2] + (parts[1] * 60) + (parts[0] * 60 * 60)

    def attempt_upgrade(self):
        """
        Attempts to upgrade or research a (new) unit type
        """
        self.logger.debug("Managing Upgrades")
        if self._research_wait > time.time():
            self.logger.debug(
                "Smith still busy for %d seconds", int(self._research_wait - time.time())
            )
            return
        unit_levels = self.wanted_levels
        if not unit_levels:
            self.logger.debug("Not upgrading because nothing is requested")
            return
        result = self.wrapper.get_action(village_id=self.village_id, action="smith")
        smith_data = Extractor.smith_data(result)
        if not smith_data:
            self.logger.debug("Error reading smith data")
            return False
        for unit_type in unit_levels:
            if not smith_data or unit_type not in smith_data["available"]:
                self.logger.warning(
                    "Unit %s does not appear to be available or smith not built yet", unit_type
                )
                continue
            wanted_level = unit_levels[unit_type]
            current_level = int(smith_data["available"][unit_type]["level"])
            data = smith_data["available"][unit_type]

            if (
                    current_level < wanted_level
                    and "can_research" in data
                    and data["can_research"]
            ):
                if "research_error" in data and data["research_error"]:
                    self.logger.debug(
                        "Skipping  of %s because of research error", unit_type
                    )
                    # Add needed resources to res manager?
                    r = True
                    if data["wood"] > self.game_data["village"]["wood"]:
                        req = data["wood"] - self.game_data["village"]["wood"]
                        self.resman.request(source="research", resource="wood", amount=req)
                        r = False
                    if data["stone"] > self.game_data["village"]["stone"]:
                        req = data["stone"] - self.game_data["village"]["stone"]
                        self.resman.request(source="research", resource="stone", amount=req)
                        r = False
                    if data["iron"] > self.game_data["village"]["iron"]:
                        req = data["iron"] - self.game_data["village"]["iron"]
                        self.resman.request(source="research", resource="iron", amount=req)
                        r = False
                    if not r:
                        self.logger.debug("Research needs resources")
                    continue
                if "error_buildings" in data and data["error_buildings"]:
                    self.logger.debug(
                        "Skipping research of %s because of building error", unit_type
                    )
                    continue

                attempt = self.attempt_research(unit_type, smith_data=smith_data)
                if attempt:
                    self.logger.info(
                        "Started smith upgrade of %s %d -> %d",
                        unit_type, current_level, current_level + 1
                    )
                    self.wrapper.reporter.report(
                        self.village_id,
                        "TWB_UPGRADE",
                        "Started smith upgrade of %s %d -> %d"
                        % (unit_type, current_level, current_level + 1),
                    )
                    return True
        return False

    def attempt_research(self, unit_type, smith_data=None):
        if not smith_data:
            result = self.wrapper.get_action(village_id=self.village_id, action="smith")
            smith_data = Extractor.smith_data(result)
        if not smith_data or unit_type not in smith_data["available"]:
            self.logger.warning(
                "Unit %s does not appear to be available or smith not built yet", unit_type
            )
            return
        data = smith_data["available"][unit_type]
        if "can_research" in data and data["can_research"]:
            if "research_error" in data and data["research_error"]:
                self.logger.debug(
                    "Ignoring research of %s because of resource error %s", unit_type, str(data["research_error"])
                )
                # Add needed resources to res manager?
                r = True
                if data["wood"] > self.game_data["village"]["wood"]:
                    req = data["wood"] - self.game_data["village"]["wood"]
                    self.resman.request(source="research", resource="wood", amount=req)
                    r = False
                if data["stone"] > self.game_data["village"]["stone"]:
                    req = data["stone"] - self.game_data["village"]["stone"]
                    self.resman.request(source="research", resource="stone", amount=req)
                    r = False
                if data["iron"] > self.game_data["village"]["iron"]:
                    req = data["iron"] - self.game_data["village"]["iron"]
                    self.resman.request(source="research", resource="iron", amount=req)
                    r = False
                if not r:
                    self.logger.debug("Research needs resources")
                return False
            if "error_buildings" in data and data["error_buildings"]:
                self.logger.debug(
                    "Ignoring research of %s because of building error %s", unit_type, str(data["error_buildings"])
                )
                return False
            if (
                    "level" in data
                    and "level_highest" in data
                    and data["level_highest"] != 0
                    and data["level"] == data["level_highest"]
            ):
                return False
            res = self.wrapper.get_api_action(
                village_id=self.village_id,
                action="research",
                params={"screen": "smith"},
                data={
                    "tech_id": unit_type,
                    "source": self.village_id,
                    "h": self.wrapper.last_h,
                },
            )
            if res:
                if "research_time" in data:
                    self._research_wait = time.time() + self.research_time(
                        data["research_time"]
                    )
                self.logger.info("Started research of %s", unit_type)
                # self.resman.update(res["game_data"])
                return True
        self.logger.info("Research of %s not yet possible", unit_type)

    def get_scavenge_status(self):
        """
        Gets current status of scavenge options using the correct method
        """
        try:
            # Use HTML page to get status
            url = f"game.php?village={self.village_id}&screen=place&mode=scavenge"
            result = self.wrapper.get_url(url)
            
            if not result:
                self.logger.error("Failed to load scavenge page")
                return None
                
            # Extract page data using existing extractor
            village_data = Extractor.village_data(result)
            
            if not village_data or 'options' not in village_data:
                self.logger.error("Failed to extract scavenge options data")
                return None
            
            if village_data and 'options' in village_data:
                options = village_data.get("options", {})
                current_time = time.time()
                
                self.logger.debug("Current scavenge options status:")
                for option_id, option_info in options.items():
                    is_locked = option_info.get("is_locked", True)
                    unlock_time = option_info.get("unlock_time")
                    has_squad = option_info.get("scavenging_squad") is not None
                    
                    status = "locked"
                    if unlock_time and unlock_time > current_time:
                        remaining = int(unlock_time - current_time)
                        status = f"unlocking ({remaining}s)"
                    elif not is_locked:
                        status = "available" if not has_squad else "in_use"
                    
                    self.logger.debug("Option %s: %s", option_id, status)
                
                return village_data
            else:
                self.logger.error("Failed to get scavenge options status")
                return None
                
        except Exception as e:
            self.logger.error("Error getting scavenge status: %s", str(e))
            return None

    def unlock_scavenge_option(self, option_id, wood_cost, stone_cost, iron_cost):
        """
        Attempts to unlock a scavenge option
        """
        try:
            self.logger.info("Unlocking scavenge option %s", option_id)
            self.logger.info("Cost: %s wood, %s stone, %s iron", wood_cost, stone_cost, iron_cost)
            
            # Update CSRF token before request
            try:
                overview_page = self.wrapper.get_action(action="overview", village_id=self.village_id)
                if overview_page and hasattr(self.wrapper, 'last_response'):
                    import re
                    h_match = re.search(r'&h=(\w+)', overview_page.text if hasattr(overview_page, 'text') else str(overview_page))
                    if h_match:
                        self.wrapper.last_h = h_match.group(1)
                        self.logger.debug("CSRF token updated")
            except Exception as token_error:
                self.logger.warning("Failed to update CSRF token: %s", str(token_error))
            
            # Prepare headers for API request
            custom_headers = dict(self.wrapper.headers)
            custom_headers.update({
                'Accept': "application/json, text/javascript, */*; q=0.01",
                'Accept-Language': "pt-BR,pt;q=0.9",
                'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
                'X-Requested-With': "XMLHttpRequest",
                'TribalWars-Ajax': "1",
                'Referer': f"https://{self.wrapper.endpoint}/game.php?village={self.village_id}&screen=place&mode=scavenge",
                'Origin': f"https://{self.wrapper.endpoint}",
                'Sec-Fetch-Dest': "empty",
                'Sec-Fetch-Mode': "cors", 
                'Sec-Fetch-Site': "same-origin"
            })
            
            # Prepare request data
            payload_data = {
                "village_id": str(self.village_id),
                "option_id": str(option_id),
                "h": self.wrapper.last_h
            }
            
            # Send unlock request
            url = f"game.php?village={self.village_id}&screen=scavenge_api&ajaxaction=start_unlock"
            
            response = self.wrapper.post_url(
                url,
                data=payload_data,
                headers=custom_headers
            )
            
            if response and response.status_code == 200:
                try:
                    result = response.json()
                except:
                    result = {"raw_response": response.text}
                    
                if result and "response" in result:
                    village_data = result["response"]["village"]
                    options = village_data.get("options", {})
                    option_str = str(option_id)
                    
                    if option_str in options:
                        option_info = options[option_str]
                        
                        # Check if unlock was initiated
                        if option_info.get("unlock_time"):
                            unlock_time = option_info["unlock_time"]
                            current_time = result.get("time_generated_ms", 0) / 1000
                            
                            time_remaining = unlock_time - current_time
                            
                            if time_remaining > 0:
                                self.logger.info("Option %s unlock started, %s seconds remaining", option_id, int(time_remaining))
                                return True
                            else:
                                self.logger.info("Option %s already unlocked", option_id)
                                return True
                                
                        elif not option_info.get("is_locked", True):
                            self.logger.info("Option %s was already unlocked", option_id)
                            return True
                        else:
                            self.logger.warning("Failed to start unlock for option %s", option_id)
                            return False
                    else:
                        self.logger.error("Option %s not found in response", option_id)
                        return False
                elif result and "error" in result:
                    error_msg = result["error"]
                    self.logger.error("API error: %s", error_msg)
                    return False
                else:
                    self.logger.error("Invalid API response: %s", result)
                    return False
            else:
                status_code = response.status_code if response else "No response"
                self.logger.error("HTTP error %s", status_code)
                return False
                
        except Exception as e:
            self.logger.error("Error unlocking option %s: %s", option_id, str(e))
            return False

    def can_afford_unlock(self, wood_cost, stone_cost, iron_cost, min_resources_after=0):
        """
        Check if there are enough resources to unlock an option
        """
        current_wood = self.game_data["village"]["wood"]
        current_stone = self.game_data["village"]["stone"] 
        current_iron = self.game_data["village"]["iron"]
        
        can_afford = (
            current_wood >= (wood_cost + min_resources_after) and
            current_stone >= (stone_cost + min_resources_after) and
            current_iron >= (iron_cost + min_resources_after)
        )
        
        self.logger.debug("Resource check for unlock - Need: %s/%s/%s, Have: %s/%s/%s, Can afford: %s",
                         wood_cost, stone_cost, iron_cost, current_wood, current_stone, current_iron, can_afford)
        
        return can_afford

    def check_unlock_progress(self):
        """
        Check progress of ongoing unlocks
        """
        try:
            village_data = self.get_scavenge_status()
            if not village_data:
                return
                
            options = village_data.get("options", {})
            current_time = time.time()
            
            for option_id, option_info in options.items():
                unlock_time = option_info.get("unlock_time")
                if unlock_time:
                    # Convert unlock_time if necessary (might be in milliseconds)
                    if unlock_time > 9999999999:
                        unlock_time = unlock_time / 1000
                        
                    time_remaining = unlock_time - current_time
                    
                    if time_remaining > 0:
                        minutes = int(time_remaining // 60)
                        seconds = int(time_remaining % 60)
                        self.logger.info("Option %s: unlocking... (%sm%ss remaining)", option_id, minutes, seconds)
                    else:
                        if option_info.get("is_locked", True):
                            self.logger.info("Option %s: unlock should be completed", option_id)
                        else:
                            self.logger.info("Option %s: unlocked successfully", option_id)
                            
        except Exception as e:
            self.logger.error("Error checking unlock progress: %s", str(e))

    def auto_unlock_scavenge_options(self, min_resources_after_unlock=0):
        """
        Automatic scavenge option unlocking system
        Checks available options, costs and attempts to unlock if resources are sufficient
        """
        try:
            # Known unlock costs
            unlock_costs = {
                1: {"wood": 25, "stone": 30, "iron": 25, "name": "Small Scavenge"},
                2: {"wood": 250, "stone": 300, "iron": 250, "name": "Medium Scavenge"},
                3: {"wood": 1000, "stone": 1200, "iron": 1000, "name": "Large Scavenge"},
                4: {"wood": 10000, "stone": 12000, "iron": 10000, "name": "Extreme Scavenge"}
            }
            
            self.logger.info("Checking auto-unlock scavenge options...")
            
            # Get current options status
            village_data = self.get_scavenge_status()
            if not village_data:
                self.logger.error("Failed to get scavenge options status")
                return False
                
            options = village_data.get("options", {})
            unlocked_any = False
            
            # Check if any unlock is in progress
            option_1_unlocked = False
            any_unlocking = False
            
            for option_id, option_info in options.items():
                unlock_time = option_info.get("unlock_time")
                if unlock_time:
                    # Convert timestamp if necessary
                    if unlock_time > 9999999999:
                        unlock_time = unlock_time / 1000
                        
                    current_time = time.time()
                    if unlock_time > current_time:
                        any_unlocking = True
                        remaining = int(unlock_time - current_time)
                        minutes = remaining // 60
                        seconds = remaining % 60
                        self.logger.info("Option %s unlocking in progress (%sm%ss remaining)", option_id, minutes, seconds)
                        
            if any_unlocking:
                self.logger.info("Unlock in progress - waiting for completion")
                return False
                        
            # Check if option 1 is unlocked
            if "1" in options and not options["1"].get("is_locked", False):
                option_1_unlocked = True
                self.logger.debug("Prerequisite: Option 1 is unlocked")
            else:
                self.logger.debug("Option 1 not yet fully unlocked")
            
            # Check each option in order (cheapest to most expensive)
            for option_num in sorted(unlock_costs.keys()):
                option_str = str(option_num)
                costs = unlock_costs[option_num]
                
                if option_str not in options:
                    self.logger.debug("Option %s does not exist", option_num)
                    continue
                    
                option_info = options[option_str]
                
                # Prerequisite check for option 2 and higher
                if option_num > 1 and not option_1_unlocked:
                    self.logger.debug("Skipping option %s - prerequisite not met (option 1 must be unlocked)", option_num)
                    continue
                
                # Check if already unlocked
                if not option_info.get("is_locked", False):
                    self.logger.debug("Option %s (%s) already unlocked", option_num, costs['name'])
                    if option_num == 1:
                        option_1_unlocked = True
                    continue
                    
                # Check if currently being unlocked
                unlock_time = option_info.get("unlock_time")
                if unlock_time:
                    if unlock_time > 9999999999:
                        unlock_time = unlock_time / 1000
                        
                    current_time = time.time()
                    time_remaining = unlock_time - current_time
                    
                    if time_remaining > 0:
                        minutes = int(time_remaining // 60)
                        seconds = int(time_remaining % 60)
                        self.logger.info("Option %s (%s) already being unlocked (%sm%ss remaining)", option_num, costs['name'], minutes, seconds)
                        continue
                        
                # Check resources
                if not self.can_afford_unlock(costs["wood"], costs["stone"], costs["iron"], min_resources_after_unlock):
                    self.logger.info("Insufficient resources for option %s (%s)", option_num, costs['name'])
                    continue
                    
                # Attempt to unlock
                self.logger.info("Starting unlock for option %s (%s)...", option_num, costs['name'])
                
                if self.unlock_scavenge_option(option_num, costs["wood"], costs["stone"], costs["iron"]):
                    unlocked_any = True
                    
                    # Update game_data after unlock
                    try:
                        time.sleep(1)
                        main_data = self.wrapper.get_action(action="overview", village_id=self.village_id)
                        if main_data:
                            self.game_data = Extractor.game_state(main_data)
                            self.logger.debug("Resources updated after unlock")
                    except Exception as e:
                        self.logger.warning("Failed to update resources: %s", str(e))
                    
                    # Stop after first successful unlock to avoid excessive spending
                    self.logger.info("Stopping after successful unlock to avoid excessive spending")
                    break
                else:
                    self.logger.warning("Failed to unlock option %s", option_num)
                    
                    # If option 2 failed, might be prerequisite or cooldown issue
                    if option_num == 2:
                        self.logger.info("If option 1 was recently unlocked, wait a few minutes")
                        
                        # Retry with delay for option 2
                        self.logger.info("Retrying after 30 second delay...")
                        time.sleep(30)
                        
                        if self.unlock_scavenge_option(option_num, costs["wood"], costs["stone"], costs["iron"]):
                            unlocked_any = True
                            self.logger.info("Unlock successful on retry")
                            break
                        else:
                            self.logger.warning("Retry also failed - waiting for next bot cycle")
            
            if not unlocked_any:
                if any_unlocking:
                    self.logger.info("Waiting for unlock completion...")
                else:
                    self.logger.info("No options could be unlocked at this time")
                
            return unlocked_any
            
        except Exception as e:
            self.logger.error("Error in auto-unlock: %s", str(e))
            return False

    def gather(self, selection=1, disabled_units=[], advanced_gather=True, auto_unlock=True, min_resources_after_unlock=0):
        """
        Used for the gather resources functionality where it uses two options:
        - Basic: all troops gather on the selected gather level
        - Advanced: troops are split
        - Auto-unlock: automatically unlocks scavenge options if possible
        - min_resources_after_unlock: minimum resources to keep after unlock
        """
        if not self.can_gather:
            return False
            
        # Auto-unlock feature
        if auto_unlock:
            try:
                self.logger.info("Checking auto-unlock scavenge options...")
                unlocked = self.auto_unlock_scavenge_options(min_resources_after_unlock)
                if unlocked:
                    self.logger.info("Options unlocked, waiting for processing...")
                    time.sleep(5)
            except Exception as e:
                self.logger.warning("Auto-unlock failed: %s", str(e))
        
        # Check unlock progress
        self.check_unlock_progress()
        
        url = f"game.php?village={self.village_id}&screen=place&mode=scavenge"
        result = self.wrapper.get_url(url=url)
        
        if not result:
            self.logger.error("Failed to load scavenge page")
            return False
            
        village_data = Extractor.village_data(result)

        sleep = 0
        available_selection = 0

        self.troops = {}

        get_all = f"game.php?village={self.village_id}&screen=place&mode=units&display=units"
        result_all = self.wrapper.get_url(get_all)

        if not result_all:
            self.logger.error("Failed to load units page")
            return False

        for u in Extractor.units_in_village(result_all):
            k, v = u
            self.troops[k] = v

        troops = dict(self.troops)

        haul_dict = [
            "spear:25",
            "sword:15",
            "axe:10",
            "heavy:50"
        ]
        if "archer" in self.total_troops:
            haul_dict.extend(["archer:10", "marcher:50"])

        # ADVANCED GATHER: Goes from gather_selection to 1, trying the same time (approximately) for every gather. Active hours exclude LC and Axes, at night everything is used for gather (except Paladin)

        if advanced_gather:
            selection_map = [15, 21, 24,
                             26]  # Divider in order to split the total carrying capacity of the troops into pieces that can fit into pretty much the same time frame

            batch_multiplier = [15, 6, 3,
                                2]  # Multiplier for equal distribution of troops. Time(gather1) = Time(gather2) if gather2 = 2.5 * gather1

            troops = {key: int(value) for key, value in troops.items()}
            total_carry = 0
            for item in haul_dict:
                item, carry = item.split(":")
                if item == "knight":
                    continue
                if item in disabled_units:
                    continue
                if item in troops and int(troops[item]) > 0:
                    total_carry += int(carry) * int(troops[item])
                else:
                    pass
            
            if total_carry == 0:
                self.logger.info("No troops available for gather")
                return False
                
            gather_batch = math.floor(total_carry / selection_map[selection - 1])

            for option in list(reversed(sorted(village_data['options'].keys())))[4 - selection:]:
                self.logger.debug(
                    f"Option: {option} Locked? {village_data['options'][option]['is_locked']} Is underway? {village_data['options'][option]['scavenging_squad'] != None}")
                if int(option) <= selection and not village_data['options'][option]['is_locked'] and village_data['options'][option]['scavenging_squad'] == None:
                    available_selection = int(option)
                    self.logger.info(f"Gather operation {available_selection} is ready to start.")

                    payload = {
                        "squad_requests[0][village_id]": self.village_id,
                        "squad_requests[0][option_id]": str(available_selection),
                        "squad_requests[0][use_premium]": "false",
                    }

                    curr_haul = gather_batch * batch_multiplier[available_selection - 1]
                    temp_haul = curr_haul

                    self.logger.debug(
                        f"Current Haul: {curr_haul} = Gather Batch ({gather_batch}) * Batch Multiplier {available_selection} ({batch_multiplier[available_selection - 1]})")

                    for item in haul_dict:
                        item, carry = item.split(":")
                        if item == "knight":
                            continue
                        if item in disabled_units:
                            continue

                        if item in troops and int(troops[item]) > 0:
                            troops_int = int(troops[item])
                            troops_selected = 0
                            for troop in range(troops_int):
                                if (temp_haul - int(carry) < 0):
                                    break
                                else:
                                    troops_selected += 1
                                    temp_haul -= int(carry)
                            troops_int -= troops_selected
                            troops[item] = str(troops_int)
                            payload["squad_requests[0][candidate_squad][unit_counts][%s]" % item] = str(troops_selected)
                        else:
                            payload["squad_requests[0][candidate_squad][unit_counts][%s]" % item] = "0"
                    payload["squad_requests[0][candidate_squad][carry_max]"] = str(curr_haul)
                    payload["h"] = self.wrapper.last_h
                    
                    try:
                        self.wrapper.get_api_action(
                            action="send_squads",
                            params={"screen": "scavenge_api"},
                            data=payload,
                            village_id=self.village_id,
                        )
                        sleep += random.randint(1, 5)
                        time.sleep(sleep)
                        self.last_gather = int(time.time())
                        self.logger.info(f"Using troops for gather operation: {available_selection}")
                    except Exception as send_error:
                        self.logger.error(f"Failed to send gather operation {available_selection}: {send_error}")
                        continue
                else:
                    # Gathering already exists or locked
                    continue

        else:
            for option in reversed(sorted(village_data['options'].keys())):
                self.logger.debug(
                    f"Option: {option} Locked? {village_data['options'][option]['is_locked']} Is underway? {village_data['options'][option]['scavenging_squad'] != None}")
                if int(option) <= selection and not village_data['options'][option]['is_locked'] and village_data['options'][option]['scavenging_squad'] == None:
                    available_selection = int(option)
                    self.logger.info(f"Gather operation {available_selection} is ready to start.")
                    selection = available_selection

                    payload = {
                        "squad_requests[0][village_id]": self.village_id,
                        "squad_requests[0][option_id]": str(available_selection),
                        "squad_requests[0][use_premium]": "false",
                    }
                    total_carry = 0
                    for item in haul_dict:
                        item, carry = item.split(":")
                        if item == "knight":
                            continue
                        if item in disabled_units:
                            continue
                        if item in troops and int(troops[item]) > 0:
                            payload[
                                "squad_requests[0][candidate_squad][unit_counts][%s]" % item
                                ] = troops[item]
                            total_carry += int(carry) * int(troops[item])
                        else:
                            payload[
                                "squad_requests[0][candidate_squad][unit_counts][%s]" % item
                                ] = "0"
                    payload["squad_requests[0][candidate_squad][carry_max]"] = str(total_carry)
                    if total_carry > 0:
                        payload["h"] = self.wrapper.last_h
                        try:
                            self.wrapper.get_api_action(
                                action="send_squads",
                                params={"screen": "scavenge_api"},
                                data=payload,
                                village_id=self.village_id,
                            )
                            self.last_gather = int(time.time())
                            self.logger.info(f"Using troops for gather operation: {selection}")
                        except Exception as send_error:
                            self.logger.error(f"Failed to send gather operation {selection}: {send_error}")
                            continue
                else:
                    # Gathering already exists or locked
                    continue
        self.logger.info("All gather operations are underway.")
        return True

    def cancel(self, building, id):
        """
        Cancel a troop recruiting action
        """
        self.wrapper.get_api_action(
            action="cancel",
            params={"screen": building},
            data={"id": id},
            village_id=self.village_id,
        )

    def recruit(self, unit_type, amount=10, wait_for=False, building="barracks"):
        """
        Recruit x amount of x from a certain building
        """
        data = self.wrapper.get_action(action=building, village_id=self.village_id)

        existing = Extractor.active_recruit_queue(data)
        if existing:
            self.logger.warning(
                "Building Village %s %s recruitment queue out-of-sync"
                % (self.village_id, building)
            )
            if not self.can_fix_queue:
                return True
            for entry in existing:
                self.cancel(building=building, id=entry)
                self.logger.info(
                    "Canceled recruit item %s on building %s" % (entry, building)
                )
            return self.recruit(unit_type, amount, wait_for, building)

        self.recruit_data = Extractor.recruit_data(data)
        self.game_data = Extractor.game_state(data)
        self.logger.info("Attempting recruitment of %d %s" % (amount, unit_type))

        if amount > self.max_batch_size:
            amount = self.max_batch_size

        if unit_type not in self.recruit_data:
            self.logger.warning(
                "Recruitment of %d %s failed because it is not researched"
                % (amount, unit_type)
            )
            self.attempt_research(unit_type)
            return False

        resources = self.recruit_data[unit_type]
        if not resources:
            self.logger.warning(
                "Recruitment of %d %s failed because invalid identifier"
                % (amount, unit_type)
            )
            return False
        if not resources["requirements_met"]:
            self.logger.warning(
                "Recruitment of %d %s failed because it is not researched"
                % (amount, unit_type)
            )
            self.attempt_research(unit_type)
            return False

        get_min = self.get_min_possible(resources)
        if get_min == 0:
            self.logger.info(
                "Recruitment of %d %s failed because of not enough resources"
                % (amount, unit_type)
            )
            self.reserve_resources(resources, amount, get_min, unit_type)
            return False

        needed_reserve = False
        if get_min < amount:
            if wait_for:
                self.logger.warning(
                    "Recruitment of %d %s failed because of not enough resources"
                    % (amount, unit_type)
                )
                self.reserve_resources(resources, amount, get_min, unit_type)
                needed_reserve = True
                return False
            if get_min > 0:
                self.logger.info(
                    "Recruitment of %d %s was set to %d because of resources"
                    % (amount, unit_type, get_min)
                )
                self.reserve_resources(resources, amount, get_min, unit_type)
                amount = get_min
                needed_reserve = True

        if not needed_reserve:
            # No need to reserve resources anymore!
            if f"recruitment_{unit_type}" in self.resman.requested:
                self.resman.requested.pop(f"recruitment_{unit_type}", None)

        result = self.wrapper.get_api_action(
            village_id=self.village_id,
            action="train",
            params={"screen": building, "mode": "train"},
            data={"units[%s]" % unit_type: str(amount)},
        )
        if "game_data" in result:
            self.resman.update(result["game_data"])
            self.wait_for[self.village_id][building] = int(time.time()) + (
                    amount * int(resources["build_time"])
            )
            # self.troops[unit_type] = str((int(self.troops[unit_type]) if unit_type in self.troops else 0) + amount)
            self.logger.info(
                "Recruitment of %d %s started (%s idle till %d)",
                    amount,
                    unit_type,
                    building,
                    self.wait_for[self.village_id][building],
            )
            self.wrapper.reporter.report(
                self.village_id,
                "TWB_RECRUIT",
                "Recruitment of %d %s started (%s idle till %d)"
                % (
                    amount,
                    unit_type,
                    building,
                    self.wait_for[self.village_id][building],
                ),
            )
            return True
        return False

    def reserve_resources(self, resources, wanted_times, has_times, unit_type):
        """
        Reserve resources for a certain recruiting action
        """
        # Resources per unit, batch wanted, batch already recruiting
        create_amount = wanted_times - has_times
        self.logger.debug(f"Requesting resources to recruit %d of %s", create_amount, unit_type)
        for res in ["wood", "stone", "iron"]:
            req = resources[res] * (wanted_times - has_times)
            self.resman.request(source=f"recruitment_{unit_type}", resource=res, amount=req)

    def readable_ts(self, seconds):
        """
        Human readable timestamp
        """
        seconds -= time.time()
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        return "%d:%02d:%02d" % (hour, minutes, seconds)

    # MÉTODOS UTILITÁRIOS ADICIONAIS PARA DEBUGGING E MONITORAMENTO

    def show_scavenge_summary(self):
        """
        Shows a complete summary of scavenge options
        """
        try:
            self.logger.info("SCAVENGE OPTIONS SUMMARY:")
            self.logger.info("=" * 50)
            
            village_data = self.get_scavenge_status()
            if not village_data:
                self.logger.error("Failed to get options data")
                return
                
            options = village_data.get("options", {})
            current_time = time.time()
            
            unlock_costs = {
                1: {"wood": 25, "stone": 30, "iron": 25, "name": "Small Scavenge"},
                2: {"wood": 250, "stone": 300, "iron": 250, "name": "Medium Scavenge"},
                3: {"wood": 1000, "stone": 1200, "iron": 1000, "name": "Large Scavenge"},
                4: {"wood": 10000, "stone": 12000, "iron": 10000, "name": "Extreme Scavenge"}
            }
            
            for option_num in sorted(unlock_costs.keys()):
                option_str = str(option_num)
                costs = unlock_costs[option_num]
                
                if option_str not in options:
                    continue
                    
                option_info = options[option_str]
                is_locked = option_info.get("is_locked", True)
                unlock_time = option_info.get("unlock_time")
                has_squad = option_info.get("scavenging_squad") is not None
                
                # Determine status
                status_text = "locked"
                extra_info = ""
                
                if unlock_time and unlock_time > current_time:
                    remaining = int(unlock_time - current_time)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    status_text = "unlocking"
                    extra_info = f" ({minutes}m{seconds}s remaining)"
                elif not is_locked:
                    status_text = "in_use" if has_squad else "available"
                        
                # Check if can afford
                can_afford = ""
                if is_locked and not unlock_time:
                    affordable = self.can_afford_unlock(costs["wood"], costs["stone"], costs["iron"])
                    can_afford = " | Can afford" if affordable else " | Insufficient resources"
                
                self.logger.info("Option %s: %s", option_num, costs['name'])
                self.logger.info("   Status: %s%s", status_text, extra_info)
                if is_locked and not unlock_time:
                    self.logger.info("   Cost: %s wood, %s stone, %s iron%s", costs['wood'], costs['stone'], costs['iron'], can_afford)
                    
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error("Error showing summary: %s", str(e))

    def debug_scavenge_page(self):
        """
        Debug method to analyze scavenge page content
        """
        try:
            self.logger.debug("DEBUG MODE - Analyzing scavenge page...")
            
            url = f"game.php?village={self.village_id}&screen=place&mode=scavenge"
            result = self.wrapper.get_url(url)
            
            if not result:
                self.logger.error("Failed to load page")
                return
            
            page_content = result.text if hasattr(result, 'text') else str(result)
            
            # Analyze page JavaScript
            import re
            
            # Search for village variable with scavenge data
            village_match = re.search(r'var village = (\{.+?\});', page_content)
            if village_match:
                try:
                    import json
                    village_js_data = json.loads(village_match.group(1))
                    
                    self.logger.debug("PAGE JAVASCRIPT DATA:")
                    if 'options' in village_js_data:
                        for opt_id, opt_data in village_js_data['options'].items():
                            is_locked = opt_data.get('is_locked', True)
                            unlock_time = opt_data.get('unlock_time')
                            status = "locked" if is_locked else "unlocked"
                            if unlock_time:
                                status += f" (unlock_time: {unlock_time})"
                            self.logger.debug("   JS Option %s: %s", opt_id, status)
                    else:
                        self.logger.warning("No 'options' data in JavaScript")
                        
                except Exception as parse_error:
                    self.logger.error("Error parsing JavaScript: %s", str(parse_error))
            else:
                self.logger.warning("Variable 'village' not found in JavaScript")
            
            # Search for unlock buttons in HTML
            unlock_buttons = re.findall(r'<[^>]*?(?:Desbloquear|unlock)[^>]*?>', page_content, re.IGNORECASE)
            self.logger.debug("Unlock buttons found: %s", len(unlock_buttons))
            
            for i, button in enumerate(unlock_buttons[:4]):  # Show only first 4
                self.logger.debug("   Button %s: %s...", i+1, button[:100])
            
            # Search for ScavengeScreen data
            scavenge_screen = re.search(r'new ScavengeScreen\((.*?)\);', page_content, re.DOTALL)
            if scavenge_screen:
                self.logger.debug("ScavengeScreen found on page")
            else:
                self.logger.warning("ScavengeScreen not found")
                
        except Exception as e:
            self.logger.error("Error in debug: %s", str(e))

    def force_unlock_option_1(self):
        """
        Forces unlock attempt for option 1 for debugging
        """
        self.logger.info("FORCE UNLOCK - Attempting option 1...")
        
        # Show debugging first
        self.debug_scavenge_page()
        
        # Try to unlock option 1
        result = self.unlock_scavenge_option(1, 25, 30, 25)
        
        if result:
            self.logger.info("Option 1 unlock successful")
        else:
            self.logger.warning("Option 1 unlock failed")
        
        return result