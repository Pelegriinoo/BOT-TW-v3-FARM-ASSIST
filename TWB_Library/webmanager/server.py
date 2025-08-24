import json
import os
import sys
from datetime import datetime, timedelta
sys.path.insert(0, "../")

from flask import Flask, jsonify, send_from_directory, request, render_template

try:
    from webmanager.helpfile import help_file, buildings
    from webmanager.utils import DataReader, BotManager, MapBuilder, BuildingTemplateManager
    from core.context import AccountContext
except ImportError:
    from helpfile import help_file, buildings
    from utils import DataReader, BotManager, MapBuilder, BuildingTemplateManager
    # Fallback para contexto
    class AccountContext:
        @staticmethod
        def get_account_path():
            return os.getcwd()
        
        @staticmethod
        def get_cache_path(subdir=""):
            if subdir:
                return os.path.join(os.getcwd(), "cache", subdir)
            return os.path.join(os.getcwd(), "cache")

bm = BotManager()

app = Flask(__name__)
app.config["DEBUG"] = True


def pre_process_bool(key, value, village_id=None):
    if village_id:
        if value:
            return '<button class="btn btn-sm btn-block btn-success" data-village-id="%s" data-type-option="%s" data-type="toggle">Enabled</button>' % (
            village_id, key)
        else:
            return '<button class="btn btn-sm btn-block btn-danger" data-village-id="%s" data-type-option="%s" data-type="toggle">Disabled</button>' % (
            village_id, key)
    if value:
        return '<button class="btn btn-sm btn-block btn-success" data-type-option="%s" data-type="toggle">Enabled</button>' % key
    else:
        return '<button class="btn btn-sm btn-block btn-danger" data-type-option="%s" data-type="toggle">Disabled</button>' % key


def preprocess_select(key, value, templates, village_id=None):
    output = '<select data-type-option="%s" data-type="select" class="form-control">' % key
    if village_id:
        output = '<select data-type-option="%s" data-village-id="%s" data-type="select" class="form-control">' % (
        key, village_id)

    for template in DataReader.template_grab(templates):
        output += '<option value="%s" %s>%s</option>' % (template, 'selected' if template == value else '', template)
    output += '</select>'
    return output


def pre_process_string(key, value, village_id=None):
    templates = {
        'units.default': 'templates.troops',
        'village.units': 'templates.troops',
        'building.default': 'templates.builder',
        'village_template.units': 'templates.troops',
        'village.building': 'templates.builder',
        'village_template.building': 'templates.builder'
    }
    if key in templates:
        return preprocess_select(key, value, templates[key], village_id)
    if village_id:
        return '<input type="text" class="form-control" data-village-id="%s" data-type="text" value="%s" data-type-option="%s" />' % (
        village_id, value, key)
    else:
        return '<input type="text" class="form-control" data-type="text" value="%s" data-type-option="%s" />' % (
            value, key)


def pre_process_number(key, value, village_id=None):
    if village_id:
        return '<input type="number" data-type="number" class="form-control" data-village-id="%s" value="%s" data-type-option="%s" />' % (
        village_id, value, key)
    return '<input type="number" data-type="number" class="form-control" value="%s" data-type-option="%s" />' % (
    value, key)


def pre_process_list(key, value, village_id=None):
    if village_id:
        return '<input type="text" data-type="list" class="form-control" data-village-id="%s" value="%s" data-type-option="%s" />' % (
        village_id, ', '.join(value), key)
    return '<input type="number" data-type="list" class="form-control" value="%s" data-type-option="%s" />' % (
    ', '.join(value), key)


def fancy(key):
    name = key
    if '.' in name:
        name = name.split('.')[1]
    name = name[0].upper() + name[1:]
    out = '<hr /><strong>%s</strong>' % name
    help_txt = None
    help_key = key
    help_key = help_key.replace('village_template', 'village')
    if help_key in help_file:
        help_txt = help_file[help_key]
    if help_txt:
        out += '<br /><i>%s</i>' % help_txt
    return out


def pre_process_config():
    # TODO get generic config
    config = sync()['config']
    to_hide = ["build", "villages"]
    sections = {}
    for section in config:
        if section in to_hide:
            continue
        config_data = ""
        for parameter in config[section]:
            value = config[section][parameter]
            kvp = "%s.%s" % (section, parameter)
            if type(value) == bool:
                config_data += '%s %s' % (fancy(kvp), pre_process_bool(kvp, value))
            if type(value) == str:
                config_data += '%s %s' % (fancy(kvp), pre_process_string(kvp, value))
            if type(value) == list:
                config_data += '%s %s' % (fancy(kvp), pre_process_list(kvp, value))
            if type(value) == int or type(value) == float:
                config_data += '%s %s' % (fancy(kvp), pre_process_number(kvp, value))
        sections[section] = config_data
    return sections


def pre_process_village_config(village_id):
    config = sync()['config']['villages']
    if village_id in config:
        config = config[village_id]
    else:
        if len(config) > 0:
            config = list(config.values())[0]
        else:
            config = {}
    config_data = ""
    for parameter in config:
        value = config[parameter]
        kvp = "village.%s" % parameter
        if type(value) == bool:
            config_data += '%s %s' % (fancy(kvp), pre_process_bool(kvp, value, village_id))
        if type(value) == str:
            config_data += '%s %s' % (fancy(kvp), pre_process_string(kvp, value, village_id))
        if type(value) == list:
            config_data += '%s %s' % (fancy(kvp), pre_process_list(kvp, value, village_id))
        if type(value) == int or type(value) == float:
            config_data += '%s %s' % (fancy(kvp), pre_process_number(kvp, value, village_id))
    return config_data


def sync():
    """Sincroniza dados usando contexto da conta"""
    reports = DataReader.cache_grab("reports")
    villages = DataReader.cache_grab("villages")
    attacks = DataReader.cache_grab("attacks")
    config = DataReader.config_grab()
    managed = DataReader.cache_grab("managed")
    bot_status = bm.is_running()

    sort_reports = {key: value for key, value in sorted(reports.items(), key=lambda item: int(item[0]))}
    n_items = {k: sort_reports[k] for k in list(sort_reports)[:100]}

    out_struct = {
        "attacks": attacks,
        "villages": villages,
        "config": config,
        "reports": n_items,
        "bot": managed,
        "status": bot_status
    }
    return out_struct


@app.route('/api/get', methods=['GET'])
def get_vars():
    return jsonify(sync())


@app.route('/bot/start')
def start_bot():
    bm.start()
    return jsonify(bm.is_running())


@app.route('/bot/stop')
def stop_bot():
    bm.stop()
    return jsonify(not bm.is_running())


@app.route('/config', methods=['GET'])
def get_config():
    return render_template('config.html', data=sync(), config=pre_process_config(), helpfile=help_file)


@app.route('/village', methods=['GET'])
def get_village_config():
    data = sync()
    vid = request.args.get("id", None)
    return render_template('village.html', data=data, config=pre_process_village_config(village_id=vid),
                           current_select=vid, helpfile=help_file)


@app.route('/map', methods=['GET'])
def get_map():
    sync_data = sync()
    center_id = request.args.get("center", None)
    center = next(iter(sync_data['bot'])) if not center_id else center_id
    map_data = json.dumps(MapBuilder.build(sync_data['villages'], current_village=center, size=15))
    return render_template('map.html', data=sync_data, map=map_data)


@app.route('/villages', methods=['GET'])
def get_village_overview():
    return render_template('villages.html', data=sync())


@app.route('/building_templates', methods=['GET', 'POST'])
def get_building_templates():
    if request.form.get('new', None):
        plain = os.path.basename(request.form.get('new'))
        if not plain.endswith('.txt'):
            plain = "%s.txt" % plain
        tempfile = '../templates/builder/%s' % plain
        if not os.path.exists(tempfile):
            with open(tempfile, 'w') as ouf:
                ouf.write("")
    selected = request.args.get('t', None)
    return render_template('templates.html',
                           templates=BuildingTemplateManager.template_cache_list(),
                           selected=selected,
                           buildings=buildings)


@app.route('/', methods=['GET'])
def get_home():
    session = DataReader.get_session()
    return render_template('bot.html', data=sync(), session=session)


@app.route('/app/js', methods=['GET'])
def get_js():
    urlpath = os.path.join(os.path.dirname(__file__), "public")
    return send_from_directory(urlpath, "js.v2.js")


@app.route('/attacks', methods=['GET'])
def get_attacks():
    return render_template('attacks.html', data=sync())


@app.route('/api/attacks/list', methods=['GET'])
def api_attacks_list():
    """Lista todos os ataques agendados da conta atual"""
    try:
        # Usa o contexto da conta para localizar attacks.json
        account_path = AccountContext.get_account_path()
        attacks_file = os.path.join(account_path, "attacks.json")
        attacks = []
        
        try:
            with open(attacks_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content and content != '{}':
                    data = json.loads(content)
                    configured_attacks = data.get("attacks", [])
                    
                    # Converter para formato da interface
                    for attack in configured_attacks:
                        # Converter arrival_time para timestamp
                        arrival_str = attack.get("arrival_time", "")
                        try:
                            # Suporte para "hoje HH:MM:SS" e "amanhã HH:MM:SS"
                            if arrival_str.startswith("hoje "):
                                time_part = arrival_str.replace("hoje ", "")
                                today = datetime.now().strftime("%d/%m/%Y")
                                arrival_str = f"{today} {time_part}"
                            elif arrival_str.startswith("amanhã "):
                                time_part = arrival_str.replace("amanhã ", "")
                                tomorrow = datetime.now() + timedelta(days=1)
                                arrival_str = f"{tomorrow.strftime('%d/%m/%Y')} {time_part}"
                            
                            # Converter para timestamp
                            dt = datetime.strptime(arrival_str, "%d/%m/%Y %H:%M:%S")
                            timestamp = dt.timestamp()
                        except (ValueError, AttributeError):
                            # Se não conseguir converter, usar timestamp atual + 1 hora
                            timestamp = datetime.now().timestamp() + 3600
                        
                        attack_data = attack.copy()
                        attack_data["arrival_timestamp"] = timestamp
                        attacks.append(attack_data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        # Depois, tentar carregar do cache do Hunter (ataques já agendados)
        cache_file = os.path.join(account_path, "cache", "hunter", "scheduled_attacks.json")
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            hunter_schedule = data.get("hunter_schedule", {})
            
            for timestamp_str, attacks_list in hunter_schedule.items():
                timestamp = float(timestamp_str)
                for attack in attacks_list:
                    # Verificar se este ataque já não está na lista (evitar duplicatas)
                    attack_id = attack.get('id', '')
                    if not any(a.get('id') == attack_id for a in attacks):
                        attack_data = attack.copy()
                        attack_data["arrival_timestamp"] = timestamp
                        attack_data["scheduled"] = True  # Marcar como já agendado
                        attacks.append(attack_data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        return jsonify({"attacks": attacks, "success": True, "count": len(attacks)})
        
    except Exception as e:
        import traceback
        print(f"Erro na API list: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "attacks": []})


@app.route('/api/attacks/add', methods=['POST'])
def api_attacks_add():
    """Adicionar novo ataque na conta atual"""
    try:
        attack_data = request.get_json()
        
        if not attack_data:
            return jsonify({"success": False, "error": "Dados não recebidos"})
        
        # Validar dados obrigatórios
        required_fields = ['id', 'source_village', 'arrival_time']
        for field in required_fields:
            if field not in attack_data or not attack_data[field]:
                return jsonify({"success": False, "error": f"Campo obrigatório: {field}"})
        
        # Verificar se tem alvo
        if not attack_data.get('target_coordinates') and not attack_data.get('target_village_id'):
            return jsonify({"success": False, "error": "Especifique target_coordinates ou target_village_id"})
        
        # Verificar tropas
        troops = attack_data.get('troops', {})
        if not troops:
            return jsonify({"success": False, "error": "Especifique as tropas"})
        
        # Verificar se há pelo menos 1 tropa com quantidade > 0
        has_troops = False
        for unit, amount in troops.items():
            try:
                if int(amount) > 0:
                    has_troops = True
                    break
            except (ValueError, TypeError):
                continue
        
        if not has_troops:
            return jsonify({"success": False, "error": "Adicione pelo menos 1 tropa com quantidade > 0"})
        
        # Carregar arquivo attacks.json da conta atual
        account_path = AccountContext.get_account_path()
        attacks_file = os.path.join(account_path, "attacks.json")
        
        try:
            with open(attacks_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content or content == '{}':
                    attacks_json = {
                        "info": {
                            "created": datetime.now().strftime("%d/%m/%Y"),
                            "description": "Ataques criados via Web Interface"
                        },
                        "attacks": []
                    }
                else:
                    attacks_json = json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            attacks_json = {
                "info": {
                    "created": datetime.now().strftime("%d/%m/%Y"),
                    "description": "Ataques criados via Web Interface"
                },
                "attacks": []
            }
        
        # Verificar se já existe ataque com mesmo ID
        existing_attacks = attacks_json.get("attacks", [])
        if any(attack.get("id") == attack_data["id"] for attack in existing_attacks):
            return jsonify({"success": False, "error": f"Já existe um ataque com ID: {attack_data['id']}"})
        
        # Limpar tropas (só manter as com quantidade > 0)
        clean_troops = {}
        for unit, amount in troops.items():
            try:
                qty = int(amount)
                if qty > 0:
                    clean_troops[unit] = qty
            except (ValueError, TypeError):
                continue
        
        # Adicionar novo ataque
        new_attack = {
            "id": attack_data["id"],
            "source_village": attack_data["source_village"],
            "arrival_time": attack_data["arrival_time"],
            "troops": clean_troops,
            "type": attack_data.get("type", "attack"),
            "enabled": attack_data.get("enabled", True),
            "notes": attack_data.get("notes", "")
        }
        
        if attack_data.get("target_coordinates"):
            new_attack["target_coordinates"] = attack_data["target_coordinates"]
        if attack_data.get("target_village_id"):
            new_attack["target_village_id"] = attack_data["target_village_id"]
        
        existing_attacks.append(new_attack)
        
        # Salvar arquivo na conta atual
        with open(attacks_file, 'w', encoding='utf-8') as f:
            json.dump(attacks_json, f, indent=4, ensure_ascii=False)
        
        return jsonify({
            "success": True, 
            "message": "Ataque adicionado com sucesso!", 
            "attack": new_attack
        })
        
    except Exception as e:
        import traceback
        print(f"Erro na API add: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"})


@app.route('/api/attacks/delete/<attack_id>', methods=['DELETE'])
def api_attacks_delete(attack_id):
    """Remover ataque da conta atual"""
    try:
        account_path = AccountContext.get_account_path()
        attacks_file = os.path.join(account_path, "attacks.json")
        
        try:
            with open(attacks_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content or content == '{}':
                    return jsonify({"success": False, "error": "Nenhum ataque encontrado"})
                attacks_json = json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return jsonify({"success": False, "error": "Arquivo de ataques não encontrado"})
        
        attacks_list = attacks_json.get("attacks", [])
        original_count = len(attacks_list)
        
        # Filtrar ataque a ser removido
        attacks_json["attacks"] = [attack for attack in attacks_list if attack.get("id") != attack_id]
        
        if len(attacks_json["attacks"]) == original_count:
            return jsonify({"success": False, "error": f"Ataque com ID '{attack_id}' não encontrado"})
        
        # Salvar arquivo na conta atual
        with open(attacks_file, 'w', encoding='utf-8') as f:
            json.dump(attacks_json, f, indent=4, ensure_ascii=False)
        
        return jsonify({"success": True, "message": "Ataque removido com sucesso!"})
        
    except Exception as e:
        import traceback
        print(f"Erro na API delete: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"})


@app.route('/api/attacks/schedule', methods=['POST'])
def api_attacks_schedule():
    """Executar agendamento dos ataques da conta atual"""
    try:
        # Importar e executar o scheduler na conta atual
        import sys
        import os
        
        # Adicionar o diretório pai ao path
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        from webmanager.attacks.scheduler import TWBAttackScheduler
        
        # Usar attacks.json da conta atual
        account_path = AccountContext.get_account_path()
        attacks_file = os.path.join(account_path, "attacks.json")
        
        scheduler = TWBAttackScheduler(attacks_file)
        scheduled_count = scheduler.schedule_attacks()
        
        return jsonify({
            "success": True, 
            "message": f"{scheduled_count} ataques agendados com sucesso!",
            "scheduled_count": scheduled_count
        })
        
    except ImportError as e:
        return jsonify({"success": False, "error": f"Erro ao importar scheduler: {str(e)}"})
    except Exception as e:
        import traceback
        print(f"Erro na API schedule: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"})


@app.route('/app/config/set', methods=['GET'])
def config_set():
    vid = request.args.get("village_id", None)
    if not vid:
        DataReader.config_set(parameter=request.args.get("parameter"), value=request.args.get("value", None))
    else:
        param = request.args.get("parameter")
        if param.startswith("village."):
            param = param.replace("village.", "")
        DataReader.village_config_set(village_id=vid, parameter=param, value=request.args.get("value", None))

    return jsonify(sync())


if len(sys.argv) > 1:
    app.run(host="localhost", port=sys.argv[1])
else:
    app.run()