#!/usr/bin/env python3
"""
Farm Assistant Manager - Integração com o assistente de saque oficial do TW
Location: game/farm_assistant.py - Sistema de farming via assistente
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
    Manager que utiliza a API oficial do Assistente de Saque
    Performance: 10x mais rápido que o método tradicional
    """
    
    def __init__(self, wrapper=None, village_id=None, troopmanager=None):
        super().__init__(wrapper, village_id, troopmanager, None)
        
        # DADOS DO ASSISTENTE
        self.game_templates = {}          # Templates extraídos do jogo
        self.assistant_targets = []       # Alvos da página do assistente
        self.logger = logging.getLogger(f"FarmAssistant.{village_id}")
        
        # SISTEMA DE TIMING HUMANIZADO
        self.farms_sent_this_session = 0
        self.session_start_time = time.time()
        self.recent_actions = []
        self._last_error = ""  # Para rastrear últimos erros
        
        # CONFIGURAÇÕES DE SIMULAÇÃO HUMANA
        self.click_patterns = {
            'fast_session': (1.2, 2.8),      # Usuário experiente
            'normal_session': (2.0, 4.5),    # Usuário normal  
            'slow_session': (3.5, 7.0),      # Usuário iniciante
            'tired_session': (4.0, 9.0)      # Usuário cansado
        }
        
    # ==================== EXTRAÇÃO DE DADOS ====================
    
    def load_assistant_page(self):
        """
        Carrega a página do assistente de farm
        """
        self.logger.info("🔄 Carregando página do assistente...")
        
        url = f"game.php?village={self.village_id}&screen=am_farm"
        response = self.wrapper.get_url(url)
        
        if not response or "am_farm" not in response.text:
            self.logger.error("❌ Erro: Não foi possível acessar o assistente")
            self.logger.info("💡 Dica: Verifique se tem premium ou acesso ao assistente")
            return None
            
        self.logger.info("✅ Página do assistente carregada com sucesso")
        return response

    def extract_templates_from_game(self, html_content):
        """
        Extrai templates configurados no jogo automaticamente
        Padrão: Accountmanager.farm.templates['t_13120']['light'] = 3;
        """
        template_pattern = r"Accountmanager\.farm\.templates\['t_(\d+)'\]\['(\w+)'\] = (\d+);"
        matches = re.findall(template_pattern, html_content)
        
        templates = {}
        for template_id, unit_type, amount in matches:
            if template_id not in templates:
                templates[template_id] = {}
            templates[template_id][unit_type] = int(amount)
        
        # Ordena templates por ID (A=menor ID, B=maior ID)
        self.game_templates = dict(sorted(templates.items()))
        
        if self.game_templates:
            self.logger.info(f"📋 Templates encontrados: {len(self.game_templates)}")
            for template_id, troops in self.game_templates.items():
                troop_desc = ", ".join([f"{k}:{v}" for k, v in troops.items()])
                self.logger.info(f"   Template {template_id}: {troop_desc}")
        else:
            self.logger.warning("⚠️ Nenhum template encontrado!")
            self.logger.info("🔧 Configure templates A/B no assistente do jogo primeiro")
        
        return self.game_templates

    def validate_template_before_use(self, template_id):
        """
        Valida se um template específico está realmente funcional
        """
        # Faz uma requisição de teste para o template
        test_url = f"game.php?village={self.village_id}&screen=am_farm"
        
        try:
            response = self.wrapper.get_url(test_url)
            if response and response.status_code == 200:
                # Verifica se o template aparece como válido no HTML
                if f'template={template_id}' in response.text:
                    return True
                else:
                    self.logger.warning(f"⚠️ Template {template_id} não encontrado na página")
                    return False
        except Exception as e:
            self.logger.debug(f"Erro ao validar template {template_id}: {e}")
            return False
        
        return False

    def extract_targets_from_assistant(self, html_content):
        """
        Extrai alvos da tabela do assistente com dados completos
        MELHORADO: Validação mais rigorosa dos templates
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        targets = []
        
        # Encontra tabela de alvos
        farm_table = soup.find('table', {'id': 'plunder_list'})
        if not farm_table:
            self.logger.warning("❌ Tabela de alvos não encontrada")
            return targets
        
        # Processa cada linha de alvo
        for row in farm_table.find_all('tr', {'id': lambda x: x and x.startswith('village_')}):
            try:
                village_id = row['id'].replace('village_', '')
                
                # Extrai coordenadas do link do relatório
                coord_link = row.find('a', href=re.compile(r'view=\d+'))
                coords = coord_link.text.strip() if coord_link else "???"
                
                # Extrai distância (penúltima coluna)
                cells = row.find_all('td')
                distance_text = cells[-4].text.strip() if len(cells) > 4 else "0"
                distance = float(distance_text) if distance_text.replace('.', '').isdigit() else 0
                
                # Verifica botões de template A/B - LOGS DETALHADOS
                template_a_btn = row.find('a', class_='farm_icon_a')
                template_b_btn = row.find('a', class_='farm_icon_b')
                
                # Extrai parâmetros dos botões (onclick) - LOGS MELHORADOS
                template_a_data = None
                template_b_data = None
                
                if template_a_btn and template_a_btn.get('onclick'):
                    # Procura padrão mais específico
                    match = re.search(r'sendUnits\(this,\s*(\d+),\s*(\d+)\)', template_a_btn['onclick'])
                    if match:
                        template_id = match.group(2)
                        village_target = match.group(1)
                        template_a_data = {'village_id': village_target, 'template_id': template_id}
                        self.logger.debug(f"🅰️ Botão A: aldeia={village_target}, template={template_id}")
                
                if template_b_btn and template_b_btn.get('onclick'):
                    # Procura padrão mais específico
                    match = re.search(r'sendUnits\(this,\s*(\d+),\s*(\d+)\)', template_b_btn['onclick'])
                    if match:
                        template_id = match.group(2)
                        village_target = match.group(1)
                        template_b_data = {'village_id': village_target, 'template_id': template_id}
                        self.logger.debug(f"🅱️ Botão B: aldeia={village_target}, template={template_id}")
                
                # Status do último ataque
                status_dot = row.find('img', src=re.compile(r'dots/(green|red|yellow)\.webp'))
                last_success = 'green.webp' in status_dot['src'] if status_dot else False
                
                # Tipo de saque (completo/parcial)
                loot_img = row.find('img', src=re.compile(r'max_loot/[01]\.webp'))
                full_loot = 'max_loot/1.webp' in loot_img['src'] if loot_img else False
                
                # Verifica se há ataques em rota
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
                
                # Só adiciona se tem pelo menos um template válido
                if template_a_data or template_b_data:
                    targets.append(target_data)
                else:
                    self.logger.debug(f"Alvo {coords} ignorado - sem templates válidos")
                
            except Exception as e:
                self.logger.debug(f"Erro ao processar alvo: {e}")
                continue
        
        # Ordena por distância
        self.assistant_targets = sorted(targets, key=lambda x: x['distance'])
        
        self.logger.info(f"🎯 {len(targets)} alvos extraídos do assistente")
        return targets

    # ==================== SIMULAÇÃO HUMANA ====================
    
    def get_human_delay(self):
        """
        Calcula delay humanizado baseado em padrões reais de usuários
        """
        # Seleciona padrão baseado no progresso da sessão
        if self.farms_sent_this_session < 5:
            pattern = self.click_patterns['fast_session']    # Início rápido
        elif self.farms_sent_this_session < 15:
            pattern = self.click_patterns['normal_session']  # Ritmo normal
        elif self.farms_sent_this_session < 25:
            pattern = self.click_patterns['slow_session']    # Desacelerando
        else:
            pattern = self.click_patterns['tired_session']   # Cansaço simulado
        
        min_delay, max_delay = pattern
        
        # Randomização com distribuição gaussiana (mais realista)
        base_delay = random.uniform(min_delay, max_delay)
        micro_variation = random.gauss(0, 0.3)  # Simula "tremor" humano
        final_delay = max(1.2, base_delay + micro_variation)
        
        # 5% de chance de pausa longa (simula distração)
        if random.random() < 0.05:
            pause_delay = random.uniform(8, 25)
            self.logger.debug(f"💭 Simulando pausa humana: {pause_delay:.1f}s")
            return pause_delay
        
        self.logger.debug(f"⏱️ Delay humanizado: {final_delay:.2f}s")
        return final_delay

    def simulate_reading_time(self, target_count):
        """
        Simula tempo que humano levaria para analisar os alvos
        """
        if target_count <= 5:
            reading_time = random.uniform(0.5, 1.5)
        elif target_count <= 15:
            reading_time = random.uniform(1.0, 3.0)
        else:
            reading_time = random.uniform(2.0, 5.0)
        
        self.logger.debug(f"📖 Simulando análise de {target_count} alvos: {reading_time:.1f}s")
        time.sleep(reading_time)

    def check_pattern_suspicion(self):
        """
        Verifica se o padrão está muito regular (suspeito)
        """
        if len(self.recent_actions) < 5:
            return False
            
        recent_delays = [action['delay'] for action in self.recent_actions[-5:]]
        delay_variance = statistics.variance(recent_delays) if len(recent_delays) > 1 else 1.0
        
        # Se variação muito baixa = suspeito
        if delay_variance < 0.2:
            self.logger.warning("⚠️ Padrão suspeito - aumentando randomização")
            # Adiciona pausa para quebrar padrão
            extra_pause = random.uniform(12, 35)
            self.logger.info(f"🛡️ Pausa anti-detecção: {extra_pause:.1f}s")
            time.sleep(extra_pause)
            return True
        return False

    # ==================== LÓGICA DE SELEÇÃO ====================
    
    def select_best_template(self, target_data):
        """
        Seleciona template baseado no histórico (inteligência do FarmGod)
        """
        template_ids = list(self.game_templates.keys())
        
        if not template_ids:
            return None
        
        # Lógica inteligente de seleção:
        # Saque COMPLETO na última → Template MENOR (A)
        if target_data['last_success'] and target_data['full_loot']:
            return template_ids[0], False  # Template A, usar botão A
        
        # Sucesso mas saque PARCIAL → Template MAIOR (B)
        if target_data['last_success'] and not target_data['full_loot']:
            return template_ids[1] if len(template_ids) > 1 else template_ids[0], True
        
        # Primeira vez ou derrota → Template médio (B)
        return template_ids[1] if len(template_ids) > 1 else template_ids[0], True

    def filter_valid_targets(self, targets):
        """
        Filtra alvos válidos para ataque
        """
        valid = []
        
        for target in targets:
            # Deve ter pelo menos um template disponível
            if not (target['template_a'] or target['template_b']):
                continue
            
            # Verifica distância
            if hasattr(self, 'farm_radius') and target['distance'] > self.farm_radius:
                continue
                
            # Evita spam em aldeias já sendo atacadas
            if target['has_attacks_in_route'] and self.farms_sent_this_session > 5:
                continue
            
            valid.append(target)
        
        max_farms = getattr(self, 'max_farms', 15)
        return valid[:max_farms]

    # ==================== ENVIO DE ATAQUES ====================
    
    def send_farm_via_assistant(self, target_data, use_template_b=False):
        """
        Envia farm usando a API oficial do assistente - MODO BOTÕES
        """
        # Seleciona dados do template correto (botão A ou B)
        template_data = target_data['template_b'] if use_template_b else target_data['template_a']
        
        if not template_data:
            self.logger.warning(f"❌ Botão {'B' if use_template_b else 'A'} não disponível: {target_data['coords']}")
            return False
        
        # URL da API do assistente
        api_url = f"game.php?village={self.village_id}&screen=am_farm&mode=farm&ajaxaction=farm&json=1"
        
        # Dados da requisição - USAR IDs DOS BOTÕES, não dos templates
        farm_data = {
            'target': template_data['village_id'],
            'template': template_data['template_id'],  # Este é o ID correto do botão
            'h': self.wrapper.last_h
        }
        
        # Headers AJAX específicos
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
        self.logger.debug(f"🎯 Clicando botão {button_name} para {target_data['coords']} (template_id: {template_data['template_id']})")
        
        try:
            # Envia requisição
            response = self.wrapper.post_url(
                url=api_url,
                data=farm_data,
                headers=ajax_headers
            )
            
            return self.process_farm_response(response, target_data, use_template_b)
            
        except Exception as e:
            self.logger.error(f"❌ Exceção ao enviar farm: {e}")
            return False

    def process_farm_response(self, response, target_data, used_template_b):
        """
        Processa resposta da API do assistente
        """
        if not response:
            return False
            
        template_name = "B" if used_template_b else "A"
        
        if response.status_code == 200:
            try:
                # Tenta decodificar JSON
                result = response.json()
                
                if result.get('success') or 'error' not in result:
                    self.logger.info(f"✅ Farm enviado: {target_data['coords']} (Template {template_name})")
                    return True
                else:
                    error_list = result.get('error', ['Erro desconhecido'])
                    error_msg = ', '.join(error_list) if isinstance(error_list, list) else str(error_list)
                    
                    # Salva último erro para análise
                    self._last_error = error_msg
                    
                    # Log específico para erro de template
                    if 'modelo ainda não foi criado' in error_msg.lower():
                        self.logger.error(f"🔧 Template {template_name} não configurado no jogo para: {target_data['coords']}")
                        self.logger.info("💡 Vá no jogo, acesse o assistente e configure templates A/B com tropas")
                        self.logger.info(f"💡 URL: game.php?village={self.village_id}&screen=am_farm")
                    else:
                        self.logger.warning(f"❌ Erro no farm: {target_data['coords']} - {error_msg}")
                    return False
                    
            except:
                # Às vezes retorna HTML
                if 'error_box' not in response.text:
                    self.logger.info(f"✅ Farm enviado: {target_data['coords']} (Template {template_name})")
                    return True
                else:
                    self.logger.warning(f"❌ Erro HTML: {target_data['coords']}")
                    return False
        else:
            self.logger.error(f"❌ HTTP {response.status_code}: {target_data['coords']}")
            return False

    # ==================== MÉTODO PRINCIPAL ====================
    
    def refresh_templates_and_targets(self):
        """
        Re-carrega templates e alvos (útil quando templates são recriados)
        """
        self.logger.info("🔄 Atualizando templates e alvos...")
        
        # Re-carrega página
        assistant_page = self.load_assistant_page()
        if not assistant_page:
            return False
            
        # Re-extrai templates
        old_template_count = len(self.game_templates)
        self.extract_templates_from_game(assistant_page.text)
        new_template_count = len(self.game_templates)
        
        if new_template_count != old_template_count:
            self.logger.info(f"🔄 Templates atualizados: {old_template_count} → {new_template_count}")
        
        # Re-extrai alvos
        self.extract_targets_from_assistant(assistant_page.text)
        
        return True

    def run_assistant_farming(self):
        """
        Executa ciclo completo de farming via assistente
        """
        self.logger.info("🚀 Iniciando farming via assistente...")
        start_time = time.time()
        
        # 1. Carrega página do assistente
        assistant_page = self.load_assistant_page()
        if not assistant_page:
            return False
        
        # Simula tempo de carregamento
        load_delay = random.uniform(1.5, 3.5)
        self.logger.debug(f"⏳ Aguardando carregamento: {load_delay:.1f}s")
        time.sleep(load_delay)
        
        # 2. Extrai dados
        templates = self.extract_templates_from_game(assistant_page.text)
        targets = self.extract_targets_from_assistant(assistant_page.text)
        
        if not templates:
            self.logger.error("❌ Configure templates A/B no assistente do jogo!")
            return False
            
        if not targets:
            self.logger.warning("❌ Nenhum alvo encontrado no assistente")
            return False
        
        # 3. Simula análise dos alvos
        self.simulate_reading_time(len(targets))
        
        # 4. Filtra alvos válidos
        valid_targets = self.filter_valid_targets(targets)
        self.logger.info(f"🎯 {len(valid_targets)} alvos válidos selecionados")
        
        if not valid_targets:
            self.logger.warning("⚠️ Nenhum alvo válido para atacar")
            return False
        
        # 5. TESTE INICIAL - Testa primeiro farm para verificar se funciona
        if valid_targets:
            self.logger.info("🧪 Testando primeiro farm...")
            first_target = valid_targets[0]
            template_result = self.select_best_template(first_target)
            
            if template_result:
                template_id, use_template_b = template_result
                test_result = self.test_single_farm(first_target, use_template_b)
                
                if not test_result:
                    self.logger.error("❌ Teste inicial falhou - pode haver problema com templates")
                    self.logger.info("💡 Verifique se os templates estão salvos corretamente no jogo")
                    return False
                else:
                    self.logger.info("✅ Teste inicial OK - continuando com farming...")
        
        # 6. Simula hesitação pré-ataque
        pre_attack_delay = random.uniform(0.8, 2.5)
        time.sleep(pre_attack_delay)
        
        # 7. Loop de ataques com timing humanizado (pulando o primeiro que já foi testado)
        successful_farms = 1  # Já contamos o teste
        failed_farms = 0
        template_errors = 0
        self.farms_sent_this_session = 1  # Já contamos o teste
        
        for i, target in enumerate(valid_targets[1:], 1):  # Começa do segundo alvo
            # Delay humanizado entre farms
            if i > 0:
                human_delay = self.get_human_delay()
                time.sleep(human_delay)
                
                # Registra ação para análise de padrões
                self.recent_actions.append({
                    'timestamp': time.time(),
                    'delay': human_delay
                })
                
                # Verifica padrões suspeitos
                if len(self.recent_actions) % 5 == 0:
                    self.check_pattern_suspicion()
            
            # Seleciona template
            template_result = self.select_best_template(target)
            if not template_result:
                continue
                
            template_id, use_template_b = template_result
            
            # Micro-hesitação (simula tempo de clique)
            time.sleep(random.uniform(0.1, 0.4))
            
            # Envia farm
            if self.send_farm_via_assistant(target, use_template_b):
                successful_farms += 1
                self.farms_sent_this_session += 1
                
                # Simula verificação visual ocasional
                if random.random() < 0.25:  # 25% das vezes
                    check_delay = random.uniform(0.5, 1.2)
                    time.sleep(check_delay)
            else:
                failed_farms += 1
                
                # Se muitos erros de template consecutivos, tenta atualizar
                if 'modelo ainda não foi criado' in str(getattr(self, '_last_error', '')):
                    template_errors += 1
                    if template_errors >= 3:
                        self.logger.warning("🔄 Muitos erros de template, tentando atualizar...")
                        if self.refresh_templates_and_targets():
                            template_errors = 0  # Reset contador
                        time.sleep(random.uniform(2.0, 4.0))
                        continue
                
                # Simula frustração em caso de erro
                error_delay = random.uniform(1.5, 4.0)
                time.sleep(error_delay)
        
        # 7. Relatório final
        total_time = time.time() - start_time
        farms_per_minute = (successful_farms / total_time) * 60 if total_time > 0 else 0
        
        self.logger.info(f"🎉 Sessão concluída:")
        self.logger.info(f"   ✅ Farms enviados: {successful_farms}/{len(valid_targets)}")
        self.logger.info(f"   ❌ Farms falharam: {failed_farms}")
        self.logger.info(f"   ⏱️ Tempo total: {total_time:.1f}s")
        self.logger.info(f"   📊 Performance: {farms_per_minute:.1f} farms/min")
        
        return successful_farms > 0

    def test_single_farm(self, target_data, use_template_b=False):
        """
        Testa um único farm para diagnóstico
        """
        template_data = target_data['template_b'] if use_template_b else target_data['template_a']
        button_name = "B" if use_template_b else "A"
        
        if not template_data:
            self.logger.error(f"❌ Botão {button_name} não disponível para {target_data['coords']}")
            return False
            
        self.logger.info(f"🧪 TESTE: Enviando farm via botão {button_name}")
        self.logger.info(f"   🎯 Alvo: {target_data['coords']}")
        self.logger.info(f"   📍 Village ID: {template_data['village_id']}")
        self.logger.info(f"   🔧 Template ID: {template_data['template_id']}")
        
        # Tenta enviar
        result = self.send_farm_via_assistant(target_data, use_template_b)
        
        if result:
            self.logger.info(f"✅ TESTE SUCESSO: Botão {button_name} funcionando!")
        else:
            self.logger.error(f"❌ TESTE FALHOU: Botão {button_name} com problema")
            
        return result

    def validate_assistant_access(self):
        """
        Valida se o assistente está acessível
        """
        try:
            test_page = self.load_assistant_page()
            if not test_page:
                return False
                
            # Verifica se tem templates configurados
            templates = self.extract_templates_from_game(test_page.text)
            if not templates:
                self.logger.warning("⚠️ Nenhum template configurado no assistente")
                return False
                
            self.logger.info("✅ Assistente validado e operacional")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação do assistente: {e}")
            return False
