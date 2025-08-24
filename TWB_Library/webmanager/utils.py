import collections
import json
import os
import subprocess
from pathlib import Path

import psutil

# Importa o contexto para suporte multi-conta
try:
    from core.context import AccountContext
except ImportError:
    # Fallback para quando não há contexto disponível
    class AccountContext:
        @staticmethod
        def get_account_path():
            return Path(os.getcwd())
        
        @staticmethod
        def get_cache_path(subdir=""):
            if subdir:
                return Path(os.getcwd()) / "cache" / subdir
            return Path(os.getcwd()) / "cache"
        
        @staticmethod
        def get_config_path():
            return Path(os.getcwd()) / "config.json"


class DataReader:
    @staticmethod
    def cache_grab(cache_location):
        """Lê cache com suporte multi-conta"""
        output = {}
        
        # Usa o contexto da conta ou fallback para sistema legado
        cache_path = AccountContext.get_cache_path(cache_location)
        
        if not cache_path.exists():
            return output
            
        for existing in cache_path.iterdir():
            if not existing.is_file() or not existing.name.endswith(".json"):
                continue
                
            try:
                with open(existing, 'r', encoding='utf-8') as f:
                    output[existing.stem] = json.load(f)
            except Exception as e:
                print(f"Cache read error for {existing}: {e}. Removing broken entry")
                existing.unlink()

        return output

    @staticmethod
    def template_grab(template_location):
        """Lê templates da biblioteca compartilhada"""
        output = []
        template_location = template_location.replace('.', '/')
        
        # Templates ficam na biblioteca compartilhada, não na conta
        library_path = Path(__file__).parent.parent
        template_path = library_path / template_location
        
        if not template_path.exists():
            return output
            
        for existing in template_path.iterdir():
            if existing.is_file() and existing.name.endswith(".txt"):
                output.append(existing.stem)
                
        return output

    @staticmethod
    def config_grab():
        """Lê config com suporte multi-conta"""
        config_path = AccountContext.get_config_path()
        
        if not config_path.exists():
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def config_set(parameter, value):
        """Define config com suporte multi-conta"""
        try:
            value = json.loads(value)
        except:
            pass
            
        config_path = AccountContext.get_config_path()
        
        if not config_path.exists():
            return False
            
        with open(config_path, 'r', encoding='utf-8') as config_file:
            template = json.load(config_file, object_pairs_hook=collections.OrderedDict)
            
            if "." in parameter:
                section, param = parameter.split('.')
                if section not in template:
                    template[section] = {}
                template[section][param] = value
            else:
                template[parameter] = value
                
            with open(config_path, 'w', encoding='utf-8') as newcf:
                json.dump(template, newcf, indent=2, sort_keys=False, ensure_ascii=False)
                print("Deployed new configuration file")
                return True

    @staticmethod
    def village_config_set(village_id, parameter, value):
        """Define config de village com suporte multi-conta"""
        config_path = AccountContext.get_config_path()
        
        if not config_path.exists():
            return False
            
        with open(config_path, 'r', encoding='utf-8') as config_file:
            template = json.load(config_file, object_pairs_hook=collections.OrderedDict)
            
            if 'villages' not in template:
                template['villages'] = {}
                
            if str(village_id) not in template['villages']:
                return False
                
            try:
                template['villages'][str(village_id)][parameter] = json.loads(value)
            except json.decoder.JSONDecodeError:
                template['villages'][str(village_id)][parameter] = value
                
            with open(config_path, 'w', encoding='utf-8') as newcf:
                json.dump(template, newcf, indent=2, sort_keys=False, ensure_ascii=False)
                print("Deployed new configuration file")
                return True

    @staticmethod
    def get_session():
        """Lê session com suporte multi-conta"""
        session_path = AccountContext.get_cache_path() / "session.json"
        
        if not session_path.exists():
            return {"raw": "", "endpoint": "None", "server": "None", "world": "None"}
            
        try:
            with open(session_path, 'r', encoding='utf-8') as session_file:
                session_data = json.load(session_file)
                
                cookies = []
                for c in session_data.get('cookies', {}):
                    cookies.append(f"{c}={session_data['cookies'][c]}")
                    
                session_data['raw'] = ';'.join(cookies)
                return session_data
        except Exception as e:
            print(f"Error reading session: {e}")
            return {"raw": "", "endpoint": "None", "server": "None", "world": "None"}


class BuildingTemplateManager:
    @staticmethod
    def template_cache_list():
        """Lista templates de construção da biblioteca compartilhada"""
        # Templates ficam na biblioteca compartilhada
        library_path = Path(__file__).parent.parent
        template_path = library_path / "templates" / "builder"
        
        output = {}
        
        if not template_path.exists():
            return output
            
        for existing in template_path.iterdir():
            if not existing.name.endswith(".txt"):
                continue
                
            try:
                with open(existing, 'r', encoding='utf-8') as template_file:
                    content = [x.strip() for x in template_file.readlines()]
                    output[existing.name] = BuildingTemplateManager.template_to_dict(content)
            except Exception as e:
                print(f"Error reading template {existing}: {e}")
                
        return output

    @staticmethod
    def template_to_dict(t_list):
        """Converte template em dicionário"""
        out_data = {}
        rows = []

        for entry in t_list:
            if entry.startswith('#') or ':' not in entry:
                continue
                
            building, next_level = entry.split(':')
            next_level = int(next_level)
            old = out_data.get(building, 0)
            
            rows.append({'building': building, 'from': old, 'to': next_level})
            out_data[building] = next_level

        return rows


class MapBuilder:
    @staticmethod
    def build(villages, current_village=None, size=None):
        """Constrói dados do mapa"""
        out_map = {}
        min_x = 999
        max_x = 0
        min_y = 999
        max_y = 0

        current_location = None
        grid_vils = {}
        extra_data = {}

        for v in villages:
            vdata = villages[v]
            x, y = vdata['location']
            
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y
                
            if current_village and vdata['id'] == current_village:
                current_location = vdata['location']
                extra_data['owner'] = vdata['owner']
                extra_data['tribe'] = vdata['tribe']
                
            grid_vils[f"{x}:{y}"] = vdata

        if current_location:
            extra_data['current_location'] = current_location