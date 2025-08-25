#!/usr/bin/env python3
"""
Farm Assistant Manager - Integration with official TW Farm Assistant
Location: game/farm_assistant.py - Assistant-based farming system
Performance: 10x faster than traditional method
"""

import re
import time
import random
import logging
import statistics
from bs4 import BeautifulSoup
from game.attack import AttackManager


class FarmAssistantManager(AttackManager):
    """
    Manager that uses the official Farm Assistant API
    Provides significant performance improvements over traditional farming
    """
    
    def __init__(self, wrapper=None, village_id=None, troopmanager=None):
        super().__init__(wrapper, village_id, troopmanager, None)
        
        # Assistant data
        self.game_templates = {}
        self.assistant_targets = []
        self.logger = logging.getLogger(f"FarmAssistant.{village_id}")
        
        # Session tracking
        self.farms_sent_this_session = 0
        self.session_start_time = time.time()
        self.recent_actions = []
        self._last_error = ""
        
        # Human simulation patterns
        self.click_patterns = {
            'fast_session': (1.2, 2.8),
            'normal_session': (2.0, 4.5),
            'slow_session': (3.5, 7.0),
            'tired_session': (4.0, 9.0)
        }
        
    def load_assistant_page(self):
        """Load the farm assistant page"""
        self.logger.info("Loading farm assistant page...")
        
        url = f"game.php?village={self.village_id}&screen=am_farm"
        response = self.wrapper.get_url(url)
        
        if not response or "am_farm" not in response.text:
            self.logger.error("Failed to access farm assistant page")
            self.logger.info("Verify premium access or assistant availability")
            return None
            
        self.logger.info("Farm assistant page loaded successfully")
        return response

    def extract_templates_from_game(self, html_content):
        """
        Extract configured templates from game JavaScript
        Pattern: Accountmanager.farm.templates['t_13120']['light'] = 3;
        """
        template_pattern = r"Accountmanager\.farm\.templates\['t_(\d+)'\]\['(\w+)'\] = (\d+);"
        matches = re.findall(template_pattern, html_content)
        
        templates = {}
        for template_id, unit_type, amount in matches:
            if template_id not in templates:
                templates[template_id] = {}
            templates[template_id][unit_type] = int(amount)
        
        # Sort templates by ID (A=lower ID, B=higher ID)
        self.game_templates = dict(sorted(templates.items()))
        
        if self.game_templates:
            self.logger.info(f"Found {len(self.game_templates)} templates")
            for template_id, troops in self.game_templates.items():
                troop_desc = ", ".join([f"{k}:{v}" for k, v in troops.items()])
                self.logger.info(f"Template {template_id}: {troop_desc}")
        else:
            self.logger.warning("No templates found")
            self.logger.info("Configure templates A/B in game assistant first")
        
        return self.game_templates

    def extract_targets_from_assistant(self, html_content):
        """Extract targets from assistant table with complete data"""
        soup = BeautifulSoup(html_content, 'html.parser')
        targets = []
        
        # Find targets table
        farm_table = soup.find('table', {'id': 'plunder_list'})
        if not farm_table:
            self.logger.warning("Farm targets table not found")
            return targets
        
        # Process each target row
        for row in farm_table.find_all('tr', {'id': lambda x: x and x.startswith('village_')}):
            try:
                village_id = row['id'].replace('village_', '')
                
                # Extract coordinates from report link
                coord_link = row.find('a', href=re.compile(r'view=\d+'))
                coords = coord_link.text.strip() if coord_link else "Unknown"
                
                # Extract distance (second to last column)
                cells = row.find_all('td')
                distance_text = cells[-4].text.strip() if len(cells) > 4 else "0"
                distance = float(distance_text) if distance_text.replace('.', '').isdigit() else 0
                
                # Find template A/B buttons
                template_a_btn = row.find('a', class_='farm_icon_a')
                template_b_btn = row.find('a', class_='farm_icon_b')
                
                # Extract button parameters from onclick
                template_a_data = None
                template_b_data = None
                
                if template_a_btn and template_a_btn.get('onclick'):
                    match = re.search(r'sendUnits\(this,\s*(\d+),\s*(\d+)\)', template_a_btn['onclick'])
                    if match:
                        template_id = match.group(2)
                        village_target = match.group(1)
                        template_a_data = {'village_id': village_target, 'template_id': template_id}
                        self.logger.debug(f"Button A: village={village_target}, template={template_id}")
                
                if template_b_btn and template_b_btn.get('onclick'):
                    match = re.search(r'sendUnits\(this,\s*(\d+),\s*(\d+)\)', template_b_btn['onclick'])
                    if match:
                        template_id = match.group(2)
                        village_target = match.group(1)
                        template_b_data = {'village_id': village_target, 'template_id': template_id}
                        self.logger.debug(f"Button B: village={village_target}, template={template_id}")
                
                # Check last attack status
                status_dot = row.find('img', src=re.compile(r'dots/(green|red|yellow)\.webp'))
                last_success = 'green.webp' in status_dot['src'] if status_dot else False
                
                # Check loot type (full/partial)
                loot_img = row.find('img', src=re.compile(r'max_loot/[01]\.webp'))
                full_loot = 'max_loot/1.webp' in loot_img['src'] if loot_img else False
                
                # Check for attacks in route
                has_attacks = bool(row.find('img', src=re.compile(r'command/attack\.webp')))
                
                target_data = {
                    'id': village_id,
                    'coords': coords,
                    'distance': distance,
                    'template_a': template_a_data,
                    'template_b': template_b_data,
                    'last_success': last_success,
                    'full_loot': full_loot,
                    'has_attacks_in_route': has_attacks
                }
                
                # Only add if has at least one valid template
                if template_a_data or template_b_data:
                    targets.append(target_data)
                else:
                    self.logger.debug(f"Target {coords} ignored - no valid templates")
                
            except Exception as e:
                self.logger.debug(f"Error processing target: {e}")
                continue
        
        # Sort by distance
        self.assistant_targets = sorted(targets, key=lambda x: x['distance'])
        
        self.logger.info(f"Extracted {len(targets)} targets from assistant")
        return targets

    def get_human_delay(self):
        """Calculate humanized delay based on real user patterns"""
        # Select pattern based on session progress
        if self.farms_sent_this_session < 5:
            pattern = self.click_patterns['fast_session']
        elif self.farms_sent_this_session < 15:
            pattern = self.click_patterns['normal_session']
        elif self.farms_sent_this_session < 25:
            pattern = self.click_patterns['slow_session']
        else:
            pattern = self.click_patterns['tired_session']
        
        min_delay, max_delay = pattern
        
        # Gaussian randomization (more realistic)
        base_delay = random.uniform(min_delay, max_delay)
        micro_variation = random.gauss(0, 0.3)
        final_delay = max(1.2, base_delay + micro_variation)
        
        # 5% chance of long pause (simulates distraction)
        if random.random() < 0.05:
            pause_delay = random.uniform(8, 25)
            self.logger.debug(f"Simulating human pause: {pause_delay:.1f}s")
            return pause_delay
        
        self.logger.debug(f"Human delay: {final_delay:.2f}s")
        return final_delay

    def simulate_reading_time(self, target_count):
        """Simulate time human would take to analyze targets"""
        if target_count <= 5:
            reading_time = random.uniform(0.5, 1.5)
        elif target_count <= 15:
            reading_time = random.uniform(1.0, 3.0)
        else:
            reading_time = random.uniform(2.0, 5.0)
        
        self.logger.debug(f"Simulating analysis of {target_count} targets: {reading_time:.1f}s")
        time.sleep(reading_time)

    def check_pattern_suspicion(self):
        """Check if pattern is too regular (suspicious)"""
        if len(self.recent_actions) < 5:
            return False
            
        recent_delays = [action['delay'] for action in self.recent_actions[-5:]]
        delay_variance = statistics.variance(recent_delays) if len(recent_delays) > 1 else 1.0
        
        # If variance too low = suspicious
        if delay_variance < 0.2:
            self.logger.warning("Suspicious pattern detected - increasing randomization")
            extra_pause = random.uniform(12, 35)
            self.logger.info(f"Anti-detection pause: {extra_pause:.1f}s")
            time.sleep(extra_pause)
            return True
        return False

    def select_best_template(self, target_data):
        """Select template based on attack history (intelligent selection)"""
        template_ids = list(self.game_templates.keys())
        
        if not template_ids:
            return None
        
        # Intelligent selection logic:
        # FULL loot last time -> SMALLER template (A)
        if target_data['last_success'] and target_data['full_loot']:
            return template_ids[0], False  # Template A, use button A
        
        # Success but PARTIAL loot -> LARGER template (B)
        if target_data['last_success'] and not target_data['full_loot']:
            return template_ids[1] if len(template_ids) > 1 else template_ids[0], True
        
        # First time or defeat -> Medium template (B)
        return template_ids[1] if len(template_ids) > 1 else template_ids[0], True

    def filter_valid_targets(self, targets):
        """Filter valid targets for attack"""
        valid = []
        
        for target in targets:
            # Must have at least one template available
            if not (target['template_a'] or target['template_b']):
                continue
            
            # Check distance
            if hasattr(self, 'farm_radius') and target['distance'] > self.farm_radius:
                continue
                
            # Avoid spam on villages already being attacked
            if target['has_attacks_in_route'] and self.farms_sent_this_session > 5:
                continue
            
            valid.append(target)
        
        max_farms = getattr(self, 'max_farms', 15)
        return valid[:max_farms]

    def send_farm_via_assistant(self, target_data, use_template_b=False):
        """Send farm using official assistant API"""
        # Select correct template data (button A or B)
        template_data = target_data['template_b'] if use_template_b else target_data['template_a']
        
        if not template_data:
            button_name = "B" if use_template_b else "A"
            self.logger.warning(f"Button {button_name} not available for {target_data['coords']}")
            return False
        
        # Assistant API URL
        api_url = f"game.php?village={self.village_id}&screen=am_farm&mode=farm&ajaxaction=farm&json=1"
        
        # Request data - CORRECTED PARAMETERS
        farm_data = {
            'target': template_data['village_id'],
            'template_id': template_data['template_id'],  # FIXED: was 'template'
            'source': self.village_id,                    # FIXED: was missing
            'h': self.wrapper.last_h
        }
        
        # AJAX headers
        ajax_headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'TribalWars-Ajax': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Referer': f'https://{self.wrapper.endpoint}/game.php?village={self.village_id}&screen=am_farm',
            'Origin': f'https://{self.wrapper.endpoint}'
        }
        
        button_name = "B" if use_template_b else "A"
        self.logger.debug(f"Clicking button {button_name} for {target_data['coords']} (template_id: {template_data['template_id']})")
        
        try:
            # Send request
            response = self.wrapper.post_url(
                url=api_url,
                data=farm_data,
                headers=ajax_headers
            )
            
            return self.process_farm_response(response, target_data, use_template_b)
            
        except Exception as e:
            self.logger.error(f"Exception sending farm: {e}")
            return False

    def process_farm_response(self, response, target_data, used_template_b):
        """Process assistant API response"""
        if not response:
            return False
            
        template_name = "B" if used_template_b else "A"
        
        if response.status_code == 200:
            try:
                # Try to decode JSON
                result = response.json()
                
                # Check for success in response
                if result.get('response', {}).get('success') or 'error' not in result:
                    self.logger.info(f"Farm sent: {target_data['coords']} (Template {template_name})")
                    return True
                else:
                    error_list = result.get('error', ['Unknown error'])
                    error_msg = ', '.join(error_list) if isinstance(error_list, list) else str(error_list)
                    
                    # Save last error for analysis
                    self._last_error = error_msg
                    
                    # Specific log for template error
                    if 'modelo ainda não foi criado' in error_msg.lower():
                        self.logger.error(f"Template {template_name} not configured in game for: {target_data['coords']}")
                        self.logger.info("Go to game assistant and configure templates A/B with troops")
                        self.logger.info(f"URL: game.php?village={self.village_id}&screen=am_farm")
                    else:
                        self.logger.warning(f"Farm error: {target_data['coords']} - {error_msg}")
                    return False
                    
            except:
                # Sometimes returns HTML
                if 'error_box' not in response.text:
                    self.logger.info(f"Farm sent: {target_data['coords']} (Template {template_name})")
                    return True
                else:
                    self.logger.warning(f"HTML error: {target_data['coords']}")
                    return False
        else:
            self.logger.error(f"HTTP {response.status_code}: {target_data['coords']}")
            return False

    def refresh_templates_and_targets(self):
        """Reload templates and targets (useful when templates are recreated)"""
        self.logger.info("Refreshing templates and targets...")
        
        # Reload page
        assistant_page = self.load_assistant_page()
        if not assistant_page:
            return False
            
        # Re-extract templates
        old_template_count = len(self.game_templates)
        self.extract_templates_from_game(assistant_page.text)
        new_template_count = len(self.game_templates)
        
        if new_template_count != old_template_count:
            self.logger.info(f"Templates updated: {old_template_count} -> {new_template_count}")
        
        # Re-extract targets
        self.extract_targets_from_assistant(assistant_page.text)
        
        return True

    def test_single_farm(self, target_data, use_template_b=False):
        """Test a single farm for diagnostics"""
        template_data = target_data['template_b'] if use_template_b else target_data['template_a']
        button_name = "B" if use_template_b else "A"
        
        if not template_data:
            self.logger.error(f"Button {button_name} not available for {target_data['coords']}")
            return False
            
        self.logger.info(f"TEST: Sending farm via button {button_name}")
        self.logger.info(f"   Target: {target_data['coords']}")
        self.logger.info(f"   Village ID: {template_data['village_id']}")
        self.logger.info(f"   Template ID: {template_data['template_id']}")
        
        # Attempt to send
        result = self.send_farm_via_assistant(target_data, use_template_b)
        
        if result:
            self.logger.info(f"TEST SUCCESS: Button {button_name} working!")
        else:
            self.logger.error(f"TEST FAILED: Button {button_name} has problems")
            
        return result

    def validate_assistant_access(self):
        """Validate if assistant is accessible"""
        try:
            test_page = self.load_assistant_page()
            if not test_page:
                return False
                
            # Check if templates are configured
            templates = self.extract_templates_from_game(test_page.text)
            if not templates:
                self.logger.warning("No templates configured in assistant")
                return False
                
            self.logger.info("Assistant validated and operational")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating assistant: {e}")
            return False

    def run_assistant_farming(self):
        """Execute complete farming cycle via assistant"""
        self.logger.info("Starting assistant farming...")
        start_time = time.time()
        
        # 1. Load assistant page
        assistant_page = self.load_assistant_page()
        if not assistant_page:
            return False
        
        # Simulate loading time
        load_delay = random.uniform(1.5, 3.5)
        self.logger.debug(f"Loading delay: {load_delay:.1f}s")
        time.sleep(load_delay)
        
        # 2. Extract data
        templates = self.extract_templates_from_game(assistant_page.text)
        targets = self.extract_targets_from_assistant(assistant_page.text)
        
        if not templates:
            self.logger.error("Configure templates A/B in game assistant!")
            return False
            
        if not targets:
            self.logger.warning("No targets found in assistant")
            return False
        
        # 3. Simulate target analysis
        self.simulate_reading_time(len(targets))
        
        # 4. Filter valid targets
        valid_targets = self.filter_valid_targets(targets)
        self.logger.info(f"Selected {len(valid_targets)} valid targets")
        
        if not valid_targets:
            self.logger.warning("No valid targets to attack")
            return False
        
        # 5. INITIAL TEST - Test first farm to verify functionality
        if valid_targets:
            self.logger.info("Testing first farm...")
            first_target = valid_targets[0]
            template_result = self.select_best_template(first_target)
            
            if template_result:
                template_id, use_template_b = template_result
                test_result = self.test_single_farm(first_target, use_template_b)
                
                if not test_result:
                    self.logger.error("Initial test failed - possible template problem")
                    self.logger.info("Verify templates are saved correctly in game")
                    return False
                else:
                    self.logger.info("Initial test OK - continuing with farming...")
        
        # 6. Simulate pre-attack hesitation
        pre_attack_delay = random.uniform(0.8, 2.5)
        time.sleep(pre_attack_delay)
        
        # 7. Attack loop with humanized timing (skip first which was already tested)
        successful_farms = 1  # Already counted the test
        failed_farms = 0
        template_errors = 0
        self.farms_sent_this_session = 1  # Already counted the test
        
        for i, target in enumerate(valid_targets[1:], 1):  # Start from second target
            # Humanized delay between farms
            if i > 0:
                human_delay = self.get_human_delay()
                time.sleep(human_delay)
                
                # Register action for pattern analysis
                self.recent_actions.append({
                    'timestamp': time.time(),
                    'delay': human_delay
                })
                
                # Check suspicious patterns
                if len(self.recent_actions) % 5 == 0:
                    self.check_pattern_suspicion()
            
            # Select template
            template_result = self.select_best_template(target)
            if not template_result:
                continue
                
            template_id, use_template_b = template_result
            
            # Micro-hesitation (simulates click time)
            time.sleep(random.uniform(0.1, 0.4))
            
            # Send farm
            if self.send_farm_via_assistant(target, use_template_b):
                successful_farms += 1
                self.farms_sent_this_session += 1
                
                # Simulate occasional visual verification
                if random.random() < 0.25:  # 25% of the time
                    check_delay = random.uniform(0.5, 1.2)
                    time.sleep(check_delay)
            else:
                failed_farms += 1
                
                # If many consecutive template errors, try to refresh
                if 'modelo ainda não foi criado' in str(getattr(self, '_last_error', '')):
                    template_errors += 1
                    if template_errors >= 3:
                        self.logger.warning("Many template errors, attempting refresh...")
                        if self.refresh_templates_and_targets():
                            template_errors = 0  # Reset counter
                        time.sleep(random.uniform(2.0, 4.0))
                        continue
                
                # Simulate frustration on error
                error_delay = random.uniform(1.5, 4.0)
                time.sleep(error_delay)
        
        # 8. Final report
        total_time = time.time() - start_time
        farms_per_minute = (successful_farms / total_time) * 60 if total_time > 0 else 0
        
        self.logger.info("Session completed:")
        self.logger.info(f"   Farms sent: {successful_farms}/{len(valid_targets)}")
        self.logger.info(f"   Farms failed: {failed_farms}")
        self.logger.info(f"   Total time: {total_time:.1f}s")
        self.logger.info(f"   Performance: {farms_per_minute:.1f} farms/min")
        
        return successful_farms > 0