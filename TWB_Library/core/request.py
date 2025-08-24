"""
Class for using one generic cookie jar, emulating a single tab
CORRIGIDO para sistema multi-contas com sistema de CAPTCHA flag
"""

import requests
import logging
import re
import time
import random
from pathlib import Path
from urllib.parse import urljoin, urlencode

# Importa contexto para multi-contas
try:
    from core.context import AccountContext
except ImportError:
    # Fallback para sistema legado
    class AccountContext:
        @staticmethod
        def get_cache_path(subdir=""):
            import os
            from pathlib import Path
            if subdir:
                return Path(os.getcwd()) / "cache" / subdir
            return Path(os.getcwd()) / "cache"

from core.filemanager import FileManager
from core.notification import Notification
from core.reporter import ReporterObject


class WebWrapper:
    """
    WebWrapper object for sending HTTP requests
    CORRIGIDO para usar arquivos da conta atual com sistema de CAPTCHA flag
    """
    web = None
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
        'upgrade-insecure-requests': '1'
    }
    endpoint = None
    logger = logging.getLogger("Requests")
    server = None
    last_response = None
    last_h = None
    priority_mode = False
    auth_endpoint = None
    reporter = None
    delay = 1.0

    def __init__(self, url, server=None, endpoint=None, reporter_enabled=False, reporter_constr=None):
        """
        Construct the session and detect variables
        """
        self.web = requests.session()
        self.auth_endpoint = url
        self.server = server
        self.endpoint = endpoint
        self.reporter = ReporterObject(enabled=reporter_enabled, connection_string=reporter_constr)

    def post_process(self, response):
        """
        Post-processes all requests and stores data used for the next request
        """
        xsrf = re.search('<meta content="(.+?)" name="csrf-token"', response.text)
        if xsrf:
            self.headers['x-csrf-token'] = xsrf.group(1)
            self.logger.debug("Set CSRF token")
        elif 'x-csrf-token' in self.headers:
            del self.headers['x-csrf-token']
        self.headers['Referer'] = response.url
        self.last_response = response
        get_h = re.search(r'&h=(\w+)', response.text)
        if get_h:
            self.last_h = get_h.group(1)

    def _get_captcha_flag_path(self):
        """
        Retorna o caminho para o arquivo de flag do CAPTCHA
        """
        try:
            return AccountContext.get_cache_path() / "captcha.flag"
        except:
            return Path("cache/captcha.flag")

    def _wait_for_captcha_resolution(self):
        """
        Aguarda resolução de CAPTCHA monitorando arquivo captcha.flag
        """
        captcha_flag = self._get_captcha_flag_path()
        
        # Cria flag de CAPTCHA ativo
        captcha_flag.parent.mkdir(parents=True, exist_ok=True)
        captcha_flag.touch()
        
        self.logger.warning("CAPTCHA flag created: %s", captcha_flag)
        self.logger.warning("Bot paused - resolve CAPTCHA using launcher_session.py")
        
        # Notificação crítica para CAPTCHA
        account_name = getattr(self, 'account_name', 'unknown')
        Notification.send_critical(f"🤖 CAPTCHA detected on {account_name} - bot paused for security")
        
        # Monitora flag até ser removida
        check_count = 0
        while captcha_flag.exists():
            check_count += 1
            elapsed_min = (check_count * 30) / 60
            
            if check_count % 4 == 0:  # Log a cada 2 minutos
                self.logger.info("Waiting for CAPTCHA resolution - %.1f minutes elapsed", elapsed_min)
            
            time.sleep(30)  # Verifica a cada 30 segundos
            
            # Timeout de segurança (20 minutos)
            # if check_count > 40:
            #     self.logger.error("CAPTCHA timeout after 20 minutes - removing flag automatically")
            #     captcha_flag.unlink(missing_ok=True)
            #     Notification.send_critical(f"⏰ CAPTCHA timeout on {account_name} - manual intervention may be required")
            #     break
        
        self.logger.info("CAPTCHA flag removed - resuming normal operation")
        Notification.send_critical(f"✅ CAPTCHA resolved on {account_name} - bot resumed")

    def get_url(self, url, headers=None):
        """
        Fetches a URL using a basic GET request
        MODIFICADO - Sistema de CAPTCHA flag
        """
        self.headers['Origin'] = (self.endpoint if self.endpoint else self.auth_endpoint).rstrip('/')
        if not self.priority_mode:
            time.sleep(random.randint(int(3 * self.delay), int(7 * self.delay)))
        url = urljoin(self.endpoint if self.endpoint else self.auth_endpoint, url)
        if not headers:
            headers = self.headers
        try:
            res = self.web.get(url=url, headers=headers)
            self.logger.debug("GET %s [%d]", url, res.status_code)
            self.post_process(res)
            
            # Verifica proteção de bot
            if 'data-bot-protect="forced"' in res.text:
                self.logger.warning("Bot protection detected")
                self.reporter.report(0, "TWB_RECAPTCHA", "CAPTCHA detected - waiting for resolution")
                
                # Sistema de flag em vez de input()
                self._wait_for_captcha_resolution()
                
                # Tenta novamente após resolução
                return self.get_url(url, headers)
            
            return res
        except Exception as e:
            self.logger.warning("GET %s: %s", url, str(e))
            return None

    def post_url(self, url, data, headers=None):
        """
        Sends a basic POST request with urlencoded postdata
        """
        if not self.priority_mode:
            time.sleep(random.randint(int(3 * self.delay), int(7 * self.delay)))
        
        self.headers['Origin'] = (self.endpoint if self.endpoint else self.auth_endpoint).rstrip('/')
        url = urljoin(self.endpoint if self.endpoint else self.auth_endpoint, url)
        enc = urlencode(data)
        if not headers:
            headers = self.headers
        try:
            res = self.web.post(url=url, data=data, headers=headers)
            self.logger.debug("POST %s %s [%d]", url, enc, res.status_code)
            self.post_process(res)
            
            # Verifica proteção também em POST
            if 'data-bot-protect="forced"' in res.text:
                self.logger.warning("Bot protection detected on POST request")
                self.reporter.report(0, "TWB_RECAPTCHA", "CAPTCHA detected on POST - waiting for resolution")
                
                # Sistema de flag
                self._wait_for_captcha_resolution()
                
                # Tenta novamente após resolução
                return self.post_url(url, data, headers)
            
            return res
        except Exception as e:
            self.logger.warning("POST %s %s: %s", url, enc, str(e))
            return None

    def start(self):
        """
        Start the bot and verify whether the last session is still valid
        CORRIGIDO para usar session.json da conta atual
        """
        session_data = FileManager.load_json_file("cache/session.json")
        if session_data:
            self.web.cookies.update(session_data['cookies'])
            get_test = self.get_url("game.php?screen=overview")
            if get_test and "game.php" in get_test.url:
                return True
            self.logger.warning("Current session cache not valid")
            Notification.send_critical("⚠️ Session expired - new cookie required")

        self.web.cookies.clear()
        self.logger.info("Session cache invalid - requesting new cookie")
        Notification.send_critical("🍪 Browser cookie required")
        
        def get_cookie_input():
            """Solicita cookie do usuário com sistema de logging limpo"""
            import sys
            max_attempts = 5
            
            for attempt in range(1, max_attempts + 1):
                try:
                    if attempt == 1:
                        self.logger.info("Please paste your browser cookie string below")
                    else:
                        self.logger.warning(f"Attempt {attempt}/{max_attempts} - empty input received")
                    
                    print("Enter browser cookie string> ", end='', flush=True)
                    result = input()
                    
                    if result and result.strip():
                        return result.strip()
                    else:
                        if attempt < max_attempts:
                            self.logger.warning("Empty cookie string - please try again")
                        
                except (EOFError, KeyboardInterrupt) as e:
                    self.logger.error(f"Input error: {e}")
                    if attempt < max_attempts:
                        self.logger.info("Trying alternative input method")
                        try:
                            result = sys.stdin.readline().strip()
                            if result:
                                return result
                        except Exception:
                            pass
            
            self.logger.error(f"Failed to get cookie input after {max_attempts} attempts")
            return None
        
        cinp = get_cookie_input()
        
        # Verifica se conseguimos obter a entrada
        if cinp is None:
            self.logger.error("Falha ao obter string de cookie")
            Notification.send_critical("❌ Não foi possível obter a string de cookie")
            return False
        
        cookies = {}
        cinp = cinp.strip()
        
        if not cinp:
            self.logger.error("Empty cookie string provided")
            Notification.send_critical("❌ Empty cookie string - authentication failed")
            return False
            
        self.logger.debug(f"Cookie string received: {len(cinp)} characters")
        
        for itt in cinp.split(';'):
            itt = itt.strip()
            kvs = itt.split("=")
            k = kvs[0]
            v = '='.join(kvs[1:])
            cookies[k] = v
        self.web.cookies.update(cookies)
        self.logger.info("Game Endpoint: %s", self.endpoint)

        # Verify if the new cookie works
        verify_test = self.get_url("game.php?screen=overview")
        if verify_test and "game.php" in verify_test.url:
            Notification.send_critical("🔐 Cookie validated successfully - bot will continue")
            
            # Atualizar nome do bot com o nome da conta TW
            self._update_bot_name_with_player_name(verify_test)
        else:
            Notification.send_critical("❌ Invalid or expired cookie - bot cannot access game")
            return False

        for c in self.web.cookies:
            cookies[c.name] = c.value

        # Salva na conta atual usando FileManager com contexto
        session_data = {
            'endpoint': self.endpoint,
            'server': self.server,
            'cookies': cookies
        }
        
        FileManager.save_json_file(session_data, "cache/session.json")
        self.logger.info("Session saved to account directory")
        
        return True

    def _update_bot_name_with_player_name(self, page_response):
        """
        Atualiza o bot_name no config com o nome real do JOGADOR (não da vila)
        """
        try:
            player_name = None
            import re
            
            # Método 1: JavaScript - TribalWars.updateGameData (PRIORIDADE MÁXIMA)
            js_patterns = [
                r'TribalWars\.updateGameData\(\{[^}]*"player"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
                r'game_data\s*=\s*\{[^}]*"player"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
                r'"player"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"'
            ]
            
            for pattern in js_patterns:
                match = re.search(pattern, page_response.text, re.IGNORECASE)
                if match:
                    potential_name = match.group(1).strip()
                    if (potential_name and 
                        len(potential_name) >= 2 and 
                        "tribal" not in potential_name.lower()):
                        player_name = potential_name
                        self.logger.info("Nome do jogador extraído via JavaScript: %s", player_name)
                        break
            
            # Método 2: Menu lateral (onde aparece o nome do jogador)
            if not player_name:
                sidebar_patterns = [
                    r'<a[^>]*href="[^"]*screen=info_player[^"]*"[^>]*>([^<]+)</a>',
                    r'Perfil.*?</[^>]*>.*?<[^>]*>([^<]+)</[^>]*>.*?Inventário'
                ]
                
                for pattern in sidebar_patterns:
                    match = re.search(pattern, page_response.text, re.IGNORECASE | re.DOTALL)
                    if match:
                        potential_name = match.group(1).strip()
                        if (potential_name and 
                            len(potential_name) >= 2 and
                            "perfil" not in potential_name.lower() and
                            "inventário" not in potential_name.lower() and
                            "tribal" not in potential_name.lower()):
                            player_name = potential_name
                            self.logger.info("Nome do jogador extraído do menu lateral: %s", player_name)
                            break
            
            if not player_name:
                self.logger.warning("Não foi possível extrair o nome do jogador")
                return
            
            # Limpa o nome
            player_name = re.sub(r'[^\w\s\-]', '', player_name).strip()
            
            if not player_name:
                self.logger.warning("Nome do jogador vazio após limpeza")
                return
            
            # Carrega config
            config_data = FileManager.load_json_file("config.json")
            if not config_data:
                self.logger.warning("Não foi possível carregar config.json")
                return
            
            # Verifica se precisa atualizar
            current_bot_name = config_data.get("notifications", {}).get("bot_name", "")
            
            needs_update = (
                "{NOME_DA_CONTA}" in current_bot_name or 
                "{nome_conta_tw}" in current_bot_name or
                "{server}" in current_bot_name or
                current_bot_name in ["TWB Bot", "TWB", ""] or
                "unknown" in current_bot_name.lower() or
                " - CONTA" in current_bot_name
            )
            
            if needs_update:
                # Criar novo nome com servidor e jogador
                server_code = config_data.get("server", {}).get("server", "server")
                
                # Extrai código do servidor
                server_match = re.search(r'(br\d+|pt\d+|en\d+|\w+\d+)', str(server_code))
                if server_match:
                    server_code = server_match.group(1)
                
                new_bot_name = f"TWB {server_code.upper()} - {player_name}"
                
                # Salva
                if "notifications" not in config_data:
                    config_data["notifications"] = {}
                
                config_data["notifications"]["bot_name"] = new_bot_name
                FileManager.save_json_file(config_data, "config.json")
                
                self.logger.info("Nome do bot atualizado para: %s", new_bot_name)
                Notification.send_critical(f"🎯 Bot configurado para jogador: {player_name} servidor {server_code.upper()}")
            else:
                self.logger.info("Nome do bot já configurado: %s", current_bot_name)
            
        except Exception as e:
            self.logger.error("Erro ao atualizar nome do bot: %s", e)

    def get_action(self, village_id, action):
        """
        Runs an action on a specific village
        """
        url = "game.php?village=%s&screen=%s" % (village_id, action)
        response = self.get_url(url)
        return response

    def get_api_data(self, village_id, action, params={}):
        """
        Fetches API data from a specific village and action
        """
        custom = dict(self.headers)
        custom['accept'] = "application/json, text/javascript, */*; q=0.01"
        custom['x-requested-with'] = "XMLHttpRequest"
        custom['tribalwars-ajax'] = "1"
        req = {
            'ajax': action,
            'village': village_id,
            'screen': 'api'
        }
        req.update(params)
        payload = f"game.php?{urlencode(req)}"
        url = urljoin(self.endpoint, payload)
        res = self.get_url(url, headers=custom)
        if res and res.status_code == 200:
            try:
                return res.json()
            except:
                return res
        return None

    def post_api_data(self, village_id, action, params={}, data={}):
        """
        Simulates an API request
        """
        custom = dict(self.headers)
        custom['accept'] = "application/json, text/javascript, */*; q=0.01"
        custom['x-requested-with'] = "XMLHttpRequest"
        custom['tribalwars-ajax'] = "1"
        req = {
            'ajax': action,
            'village': village_id,
            'screen': 'api'
        }
        req.update(params)
        payload = f"game.php?{urlencode(req)}"
        url = urljoin(self.endpoint, payload)
        if 'h' not in data:
            data['h'] = self.last_h
        res = self.post_url(url, data=data, headers=custom)
        if res and res.status_code == 200:
            try:
                return res.json()
            except:
                return res
        return None

    def get_api_action(self, village_id, action, params={}, data={}):
        """
        Simulates an API action being triggered
        """
        custom = dict(self.headers)
        custom['Accept'] = "application/json, text/javascript, */*; q=0.01"
        custom['X-Requested-With'] = "XMLHttpRequest"
        custom['TribalWars-Ajax'] = "1"
        req = {
            'ajaxaction': action,
            'village': village_id,
            'screen': 'api'
        }
        req.update(params)
        payload = f"game.php?{urlencode(req)}"
        url = urljoin(self.endpoint, payload)
        if 'h' not in data:
            data['h'] = self.last_h
        res = self.post_url(url, data=data, headers=custom)
        if res and res.status_code == 200:
            try:
                return res.json()
            except:
                return res
        return None
