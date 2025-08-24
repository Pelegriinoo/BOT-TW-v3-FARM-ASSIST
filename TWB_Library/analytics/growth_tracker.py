# TWB_Library/analytics/growth_tracker.py
"""
Sistema de Monitoramento de Crescimento para TWB - 3 SNAPSHOTS POR DIA
Utiliza dados coletados pelo TWB em cache/managed/*.json
Controle integrado no config.json
"""

import json
import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

# Import FileManager para compatibilidade com sistema multi-conta
from core.filemanager import FileManager


@dataclass
class GrowthSnapshot:
    """Snapshot de dados de uma vila"""
    timestamp: str
    village_id: str
    village_name: str
    points: int
    population: int
    wood: int
    stone: int
    iron: int
    farm_used: int
    farm_capacity: int
    storage_capacity: int
    building_levels: Dict[str, int]
    total_troops: int
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'village_id': self.village_id,
            'village_name': self.village_name,
            'points': self.points,
            'population': self.population,
            'wood': self.wood,
            'stone': self.stone,
            'iron': self.iron,
            'farm_used': self.farm_used,
            'farm_capacity': self.farm_capacity,
            'storage_capacity': self.storage_capacity,
            'building_levels': self.building_levels,
            'total_troops': self.total_troops
        }


class DailySnapshotController:
    """
    Controla exatamente 3 snapshots por dia usando config.json
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # HORÁRIOS ALVO (flexíveis)
        self.target_hours = [6, 14, 20]  # 6h, 14h, 20h
        self.tolerance_hours = 4  # Aceita até 4h de diferença
    
    def _load_control_data(self) -> Dict:
        """Carrega dados de controle do config.json"""
        try:
            config = FileManager.load_json_file("config.json")
            if config and "growth_snapshots" in config:
                return config["growth_snapshots"]
            return {}
        except Exception:
            return {}
    
    def _save_control_data(self, data: Dict):
        """Salva dados de controle no config.json"""
        try:
            config = FileManager.load_json_file("config.json")
            if not config:
                self.logger.error("config.json não encontrado")
                return
            
            config["growth_snapshots"] = data
            FileManager.save_json_file(config, "config.json")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar controle no config.json: {e}")
    
    def should_take_snapshot(self) -> Tuple[bool, str]:
        """
        Verifica se deve tirar snapshot
        
        Returns:
            tuple: (should_take, reason)
        """
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_hour = now.hour
        
        # Carregar dados do dia
        control_data = self._load_control_data()
        
        # Se é um novo dia, resetar contador
        if control_data.get("date") != today:
            control_data = {
                "date": today,
                "snapshots_taken": [],
                "count": 0
            }
            self._save_control_data(control_data)
            self.logger.info(f"Novo dia detectado: {today}")
        
        snapshots_taken = control_data.get("snapshots_taken", [])
        count = len(snapshots_taken)
        
        # Já tirou 3 snapshots hoje
        if count >= 3:
            return False, f"LIMITE_DIARIO_ATINGIDO (3/3 snapshots hoje)"
        
        # Verificar se é hora de tirar snapshot
        for i, target_hour in enumerate(self.target_hours):
            # Se já tirou snapshot nesta faixa horária
            slot_taken = any(
                target_hour - self.tolerance_hours <= 
                datetime.datetime.fromisoformat(ts).hour <= 
                target_hour + self.tolerance_hours
                for ts in snapshots_taken
            )
            
            if slot_taken:
                continue
            
            # Se está na janela de tempo para este slot
            min_hour = target_hour - self.tolerance_hours
            max_hour = target_hour + self.tolerance_hours
            
            if min_hour <= current_hour <= max_hour:
                snapshot_number = count + 1
                return True, f"SLOT_{i+1} ({snapshot_number}/3 - ~{target_hour}h)"
        
        # Snapshot de emergência - se é final do dia e faltam snapshots
        if current_hour >= 22 and count < 3:
            return True, f"EMERGENCIA_FINAL_DIA ({count}/3 snapshots)"
        
        # Calcular próximo horário
        next_target = None
        for target_hour in self.target_hours:
            slot_taken = any(
                target_hour - self.tolerance_hours <= 
                datetime.datetime.fromisoformat(ts).hour <= 
                target_hour + self.tolerance_hours
                for ts in snapshots_taken
            )
            
            if not slot_taken and current_hour < target_hour + self.tolerance_hours:
                next_target = target_hour
                break
        
        if next_target:
            return False, f"AGUARDANDO_SLOT (~{next_target}h, {count}/3 hoje)"
        else:
            return False, f"TODOS_SLOTS_PREENCHIDOS ({count}/3 hoje)"
    
    def register_snapshot(self):
        """Registra que um snapshot foi tirado"""
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        control_data = self._load_control_data()
        
        if control_data.get("date") != today:
            control_data = {"date": today, "snapshots_taken": []}
        
        control_data["snapshots_taken"].append(now.isoformat())
        control_data["count"] = len(control_data["snapshots_taken"])
        
        self._save_control_data(control_data)
        self.logger.info(f"Snapshot registrado: {control_data['count']}/3 hoje")
    
    def get_daily_status(self) -> Dict:
        """Retorna status do dia atual"""
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        control_data = self._load_control_data()
        
        if control_data.get("date") != today:
            return {
                "date": today,
                "snapshots_count": 0,
                "snapshots_taken": [],
                "remaining": 3,
                "next_target": self.target_hours[0]
            }
        
        snapshots_taken = control_data.get("snapshots_taken", [])
        count = len(snapshots_taken)
        
        # Próximo alvo
        next_target = None
        for target_hour in self.target_hours:
            slot_taken = any(
                target_hour - self.tolerance_hours <= 
                datetime.datetime.fromisoformat(ts).hour <= 
                target_hour + self.tolerance_hours
                for ts in snapshots_taken
            )
            
            if not slot_taken:
                next_target = target_hour
                break
        
        return {
            "date": today,
            "snapshots_count": count,
            "snapshots_taken": [
                datetime.datetime.fromisoformat(ts).strftime("%H:%M:%S")
                for ts in snapshots_taken
            ],
            "remaining": 3 - count,
            "next_target": next_target
        }


class SimpleGrowthTracker:
    """
    Tracker de crescimento com 3 snapshots por dia
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.growth_history_file = "analytics/growth_history.json"
        
        # Garantir que o contexto da conta esteja configurado
        self._ensure_account_context()
        
        self.history = self._load_history()
        self.controller = DailySnapshotController()
    
    def _ensure_account_context(self):
        """Garante que o contexto da conta esteja configurado"""
        try:
            from core.context import AccountContext
            import os
            from pathlib import Path
            
            # Se não está em modo multi-conta, configurar baseado no diretório atual
            if not AccountContext.is_multi_account_mode():
                current_path = Path(os.getcwd())
                # Se estamos numa pasta de conta (contém config.json), configurar contexto
                if (current_path / "config.json").exists():
                    AccountContext.set_account_path(current_path)
                    self.logger.info(f"Contexto da conta configurado para: {current_path}")
        except Exception as e:
            self.logger.warning(f"Não foi possível configurar contexto da conta: {e}")
    
    def _load_history(self) -> Dict:
        """Carrega histórico de crescimento usando FileManager"""
        try:
            data = FileManager.load_json_file(self.growth_history_file)
            return data if data else {}
        except Exception as e:
            self.logger.error(f"Erro ao carregar histórico: {e}")
        return {}
    
    def _save_history(self):
        """Salva histórico de crescimento usando FileManager"""
        try:
            FileManager.save_json_file(self.history, self.growth_history_file)
            self.logger.debug(f"Histórico salvo: {self.growth_history_file}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar histórico: {e}")
            raise
    
    def collect_from_managed_cache(self) -> Dict[str, GrowthSnapshot]:
        """
        Coleta dados das vilas do cache managed usando FileManager
        """
        snapshots = {}
        
        if not FileManager.path_exists("cache/managed"):
            self.logger.warning("Diretório cache/managed não encontrado")
            return snapshots
        
        try:
            # Usar FileManager para listar arquivos
            json_files = FileManager.list_directory("cache/managed", ends_with=".json")
            self.logger.debug(f"Processando {len(json_files)} arquivos de vila")
            
            for json_file in json_files:
                village_id = json_file.replace('.json', '')
                file_path = f"cache/managed/{json_file}"
                
                try:
                    village_data = FileManager.load_json_file(file_path)
                    
                    if village_data:
                        snapshot = self._create_snapshot_from_managed_data(village_id, village_data)
                        if snapshot:
                            snapshots[village_id] = snapshot
                            
                except Exception as e:
                    self.logger.error(f"Erro ao processar vila {village_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Erro ao listar arquivos managed: {e}")
        
        return snapshots
    
    def _create_snapshot_from_managed_data(self, village_id: str, data: Dict) -> Optional[GrowthSnapshot]:
        """
        Cria snapshot a partir dos dados do cache managed
        """
        try:
            public_data = data.get('public', {})
            resources = data.get('resources', {})
            
            # Primeiro tenta a chave correta, depois o typo conhecido para compatibilidade
            building_levels = data.get('building_levels', {})
            if not building_levels:
                building_levels = data.get('buidling_levels', {})
                if building_levels:
                    self.logger.debug(f"Usando 'buidling_levels' para vila {village_id}")
            
            troops = data.get('troops', {})
            
            # Calcular capacidades
            farm_level = building_levels.get('farm', 1)
            storage_level = building_levels.get('storage', 1)
            farm_capacity = self._calculate_farm_capacity(farm_level)
            storage_capacity = self._calculate_storage_capacity(storage_level)
            
            # Calcular total de tropas
            total_troops = 0
            for count in troops.values():
                if str(count).isdigit():
                    total_troops += int(count)
            
            snapshot = GrowthSnapshot(
                timestamp=datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                village_id=village_id,
                village_name=data.get('name', f'Vila {village_id}'),
                points=public_data.get('points', 0),
                population=resources.get('pop', 0),
                wood=resources.get('wood', 0),
                stone=resources.get('stone', 0),
                iron=resources.get('iron', 0),
                farm_used=resources.get('pop', 0),
                farm_capacity=farm_capacity,
                storage_capacity=storage_capacity,
                building_levels=building_levels,
                total_troops=total_troops
            )
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Erro ao criar snapshot para vila {village_id}: {e}")
            return None
    
    def _calculate_farm_capacity(self, farm_level: int) -> int:
        """Calcula capacidade da fazenda baseado no nível"""
        return 240 + (farm_level - 1) * 20
    
    def _calculate_storage_capacity(self, storage_level: int) -> int:
        """Calcula capacidade do armazém baseado no nível"""
        base = 1000
        multiplier = 1.229951
        return int(base * (multiplier ** (storage_level - 1)))
    
    def save_current_state(self, force: bool = False) -> bool:
        """
        Salva snapshot se for necessário
        
        Args:
            force: Se True, força salvamento ignorando controle diário
        """
        # Verificar se deve coletar (a menos que seja forçado)
        if not force:
            should_take, reason = self.controller.should_take_snapshot()
            if not should_take:
                self.logger.debug(f"Snapshot não coletado: {reason}")
                return False
            else:
                self.logger.info(f"Coletando snapshot: {reason}")
        
        current_snapshots = self.collect_from_managed_cache()
        
        if not current_snapshots:
            self.logger.warning("Nenhum dado coletado para salvar")
            if not FileManager.path_exists("cache/managed"):
                self.logger.error("Diretório cache/managed não existe")
            else:
                files = FileManager.list_directory("cache/managed", ends_with=".json")
                if not files:
                    self.logger.error("Nenhum arquivo JSON em cache/managed")
                else:
                    self.logger.error(f"Arquivos encontrados mas dados inválidos: {len(files)}")
            return False
        
        timestamp_iso = datetime.datetime.now().isoformat()
        
        # Organizar por vila
        villages_saved = 0
        for village_id, snapshot in current_snapshots.items():
            if village_id not in self.history:
                self.history[village_id] = []
            
            self.history[village_id].append({
                'timestamp': timestamp_iso,
                'data': snapshot.to_dict()
            })
            
            # Manter últimos 500 registros por vila
            if len(self.history[village_id]) > 500:
                self.history[village_id] = self.history[village_id][-500:]
            
            villages_saved += 1
        
        # Salvar histórico
        self._save_history()
        
        # Registrar no controle diário
        if not force:
            self.controller.register_snapshot()
        
        status = self.controller.get_daily_status()
        self.logger.info(f"Snapshot salvo para {villages_saved} vilas ({status['snapshots_count']}/3 hoje)")
        
        return True
    
    def get_daily_status(self) -> Dict:
        """Retorna status dos snapshots do dia"""
        return self.controller.get_daily_status()
    
    def get_growth_stats(self, village_id: str = None) -> Dict:
        """
        Calcula estatísticas de crescimento
        """
        try:
            if village_id:
                if village_id not in self.history:
                    return {'error': f'Vila {village_id} não encontrada no histórico'}
                
                records = self.history[village_id]
                if len(records) < 2:
                    return {'error': 'Poucos dados para calcular crescimento'}
                
                # Calcular crescimento entre primeiro e último registro
                first_record = records[0]['data']
                last_record = records[-1]['data']
                
                # Calcular diferença de tempo em dias
                first_time = datetime.datetime.fromisoformat(records[0]['timestamp'])
                last_time = datetime.datetime.fromisoformat(records[-1]['timestamp'])
                days_diff = (last_time - first_time).days
                
                if days_diff == 0:
                    days_diff = 1
                
                points_growth = last_record['points'] - first_record['points']
                points_per_day = points_growth / days_diff
                
                return {
                    'village_name': last_record['village_name'],
                    'monitoring_days': days_diff,
                    'points_growth': points_growth,
                    'points_per_day': round(points_per_day, 2),
                    'current_points': last_record['points'],
                    'records_count': len(records),
                    'last_snapshot': records[-1]['timestamp']
                }
            else:
                # Estatísticas de todas as vilas
                all_stats = {}
                for vid in self.history.keys():
                    stats = self.get_growth_stats(vid)
                    if 'error' not in stats:
                        all_stats[vid] = stats
                
                return all_stats
            
        except Exception as e:
            self.logger.error(f"Erro ao calcular estatísticas: {e}")
            return {'error': f'Erro ao calcular estatísticas: {e}'}
    
    def get_village_timeline(self, village_id: str) -> List[Dict]:
        """
        Retorna timeline de crescimento de uma vila
        """
        if village_id not in self.history:
            return []
        
        timeline = []
        for record in self.history[village_id]:
            data = record['data']
            timeline.append({
                'timestamp': record['timestamp'],
                'points': data['points'],
                'population': data['population'],
                'wood': data['wood'],
                'stone': data['stone'],
                'iron': data['iron']
            })
        
        return timeline
    
    def print_status_report(self):
        """
        Exibe relatório de status do crescimento
        """
        current_state = self.collect_from_managed_cache()
        daily_status = self.get_daily_status()
        
        print("\n" + "="*60)
        print("RELATÓRIO DE CRESCIMENTO - 3 SNAPSHOTS/DIA")
        print("="*60)
        
        print(f"\nStatus Diário ({daily_status['date']}):")
        print(f"   Snapshots hoje: {daily_status['snapshots_count']}/3")
        if daily_status['snapshots_taken']:
            print(f"   Horários: {', '.join(daily_status['snapshots_taken'])}")
        if daily_status['next_target']:
            print(f"   Próximo alvo: ~{daily_status['next_target']}h")
        else:
            print(f"   Status: Completo para hoje")
        
        if not current_state:
            print("\nNenhuma vila encontrada no cache managed")
            return
        
        print(f"\nVilas monitoradas: {len(current_state)}")
        for village_id, snapshot in current_state.items():
            print(f"\n{snapshot.village_name} (ID: {village_id})")
            print(f"   Pontos: {snapshot.points:,}")
            print(f"   População: {snapshot.population}/{snapshot.farm_capacity}")
            print(f"   Recursos: {snapshot.wood} madeira, {snapshot.stone} argila, {snapshot.iron} ferro")
        
        print("\n" + "="*60)


def integrate_growth_tracker(twb_instance):
    """
    Integra o tracker de crescimento ao TWB
    """
    try:
        if not hasattr(twb_instance, 'growth_tracker'):
            twb_instance.growth_tracker = SimpleGrowthTracker()
            logging.info("Growth Tracker integrado com sucesso")
            return True
        return True
    except Exception as e:
        logging.error(f"Erro ao integrar Growth Tracker: {e}")
        return False


class GrowthCommands:
    """Comandos para controle do monitoramento"""
    
    @staticmethod
    def save_now(twb_instance):
        """Salva snapshot se necessário (respeitando limite diário)"""
        if hasattr(twb_instance, 'growth_tracker'):
            return twb_instance.growth_tracker.save_current_state()
        logging.warning("Growth Tracker não está integrado")
        return False
    
    @staticmethod
    def force_snapshot(twb_instance):
        """Força snapshot ignorando limite diário"""
        if hasattr(twb_instance, 'growth_tracker'):
            return twb_instance.growth_tracker.save_current_state(force=True)
        logging.warning("Growth Tracker não está integrado")
        return False
    
    @staticmethod
    def show_status(twb_instance):
        """Mostra status dos snapshots"""
        if hasattr(twb_instance, 'growth_tracker'):
            twb_instance.growth_tracker.print_status_report()
            return True
        logging.warning("Growth Tracker não está integrado")
        return False
    
    @staticmethod
    def get_daily_status(twb_instance):
        """Retorna status do dia atual"""
        if hasattr(twb_instance, 'growth_tracker'):
            return twb_instance.growth_tracker.get_daily_status()
        return {}
    
    @staticmethod
    def get_stats(twb_instance, village_id=None):
        """Obtém estatísticas de crescimento"""
        if hasattr(twb_instance, 'growth_tracker'):
            return twb_instance.growth_tracker.get_growth_stats(village_id)
        return {}