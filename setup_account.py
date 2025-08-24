#!/usr/bin/env python3
"""
Setup para nova conta no sistema TWB Multi-Contas
Cria estrutura isolada para cada conta
"""
import os
import json
from pathlib import Path

def setup_account(account_name, base_config=None):
    """Configura uma nova conta com isolamento total"""
    print(f"Configurando conta: {account_name}")
    
    # Diretórios
    base_dir = Path(__file__).parent
    accounts_dir = base_dir / "accounts"
    account_dir = accounts_dir / account_name
    
    # Cria estrutura de diretórios
    account_dir.mkdir(parents=True, exist_ok=True)
    print(f"Diretório criado: {account_dir}")
    
    # Estrutura de cache isolada (incluindo analytics para sistema de crescimento)
    cache_folders = [
        "cache",
        "cache/attacks", 
        "cache/hunter", 
        "cache/logs", 
        "cache/managed", 
        "cache/reports", 
        "cache/villages", 
        "cache/world",
        "analytics",
        "analytics/charts"
    ]
    
    for folder in cache_folders:
        folder_path = account_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)
    
    print("Estrutura de cache criada")
    
    # Config isolado
    config_file = account_dir / "config.json"
    if not config_file.exists():
        if base_config and Path(base_config).exists():
            # Copia config base se fornecido
            with open(base_config, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        else:
            # Usa template padrão
            template_file = base_dir / "config.example.json"
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                print("ERRO: Template config.example.json não encontrado")
                return False
        
        # Personaliza config para a conta
        if "notifications" in config_data and "bot_name" in config_data["notifications"]:
            server_code = config_data.get("server", {}).get("server", "server")
            config_data["notifications"]["bot_name"] = f"TWB {server_code} - {account_name}"
        
        # Salva config isolado
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"Config criado: {config_file}")
    else:
        print(f"Config já existe: {config_file}")
    
    # Session será criado automaticamente quando necessário
    cache_session_dir = account_dir / "cache"
    cache_session_dir.mkdir(exist_ok=True)
    print("Diretório de cache preparado (session.json será criado na primeira execução)")
    
    # Attacks isolado
    attacks_file = account_dir / "attacks.json"
    if not attacks_file.exists():
        with open(attacks_file, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)
        
        print(f"Attacks criado: {attacks_file}")
    
    # Launcher corrigido com sistema de crescimento integrado
    launcher_content = f'''#!/usr/bin/env python3
"""
Launcher para {account_name} no sistema TWB Multi-Contas
Define contexto da conta antes de importar TWB
"""
import sys
import os
from pathlib import Path

# Configurar path para TWB_Library ANTES de qualquer importação
current_dir = Path(__file__).parent
twb_library_path = current_dir.parent.parent / "TWB_Library"
if str(twb_library_path) not in sys.path:
    sys.path.insert(0, str(twb_library_path))

def setup_account_context():
    """Configura o contexto da conta antes de importar TWB"""
    account_name = current_dir.name
    
    # Define o diretório de trabalho para a conta
    os.chdir(current_dir)
    
    # Configuração silenciosa - logs serão exibidos pelo TWB
    
    # Importa e configura o contexto da conta ANTES de importar TWB
    try:
        from core.context import AccountContext
        AccountContext.set_account_path(current_dir)
        AccountContext.ensure_cache_dirs()
        
        return account_name, current_dir
        
    except ImportError as e:
        print(f"Erro ao importar AccountContext: {{e}}")
        print("Verifique se TWB_Library/core/context.py existe")
        raise

def verify_account_files(account_dir):
    """Verifica se arquivos essenciais existem"""
    config_file = account_dir / "config.json"
    if not config_file.exists():
        print(f"Arquivo config.json não encontrado em {{config_file}}")
        print("Execute: python setup_account.py {{account_name}}")
        return False
    
    attacks_file = account_dir / "attacks.json"
    if not attacks_file.exists():
        print("Arquivo attacks.json não encontrado, será criado vazio")
        with open(attacks_file, 'w', encoding='utf-8') as f:
            import json
            json.dump([], f, indent=2)
    
    return True


# ==========================================
# SISTEMA DE CRESCIMENTO (AUTO-ADICIONADO)
# ==========================================
from analytics.growth_tracker import integrate_growth_tracker, GrowthCommands
import datetime

def is_within_time_window(current_time, start_time, end_time):
    """Verifica se horário atual está dentro da janela"""
    from datetime import datetime as dt
    current = dt.strptime(current_time, "%H:%M").time()
    start = dt.strptime(start_time, "%H:%M").time()
    end = dt.strptime(end_time, "%H:%M").time()
    return start <= current <= end

# CONFIGURAÇÃO DAS JANELAS (3 snapshots/dia)
COLLECTION_WINDOWS = {{
    "morning": {{"start": "00:00", "end": "01:00"}},     # Logo após 00:00
    "afternoon": {{"start": "17:00", "end": "17:30"}},   # 17h da tarde
    "evening": {{"start": "23:30", "end": "23:59"}}      # Antes das 23:59
}}

# Controle de coletas diárias (uma vez por execução)
collected_today = {{
    "morning": False,
    "afternoon": False, 
    "evening": False,
    "date": ""
}}

def setup_growth_tracking(twb_instance):
    """Setup inicial do sistema de crescimento"""
    global collected_today
    integrate_growth_tracker(twb_instance)
    print(f"📊 Sistema de crescimento ativado para conta {{os.path.basename(os.getcwd())}}")

def check_growth_collection(twb_instance):
    """Verifica se deve coletar snapshot neste ciclo"""
    global collected_today
    
    current_time = datetime.datetime.now()
    current_hour_min = current_time.strftime("%H:%M")
    current_date = current_time.strftime("%Y-%m-%d")
    
    # Reset automático a cada novo dia
    if current_date != collected_today["date"]:
        collected_today = {{
            "morning": False, "afternoon": False, "evening": False, 
            "date": current_date
        }}
        print(f"📅 {{os.path.basename(os.getcwd())}}: Novo dia {{current_date}} - Reset das coletas")
    
    # Verificar cada janela de coleta
    for window_name, window_time in COLLECTION_WINDOWS.items():
        
        # Se estamos dentro da janela E ainda não coletamos hoje
        if (is_within_time_window(current_hour_min, window_time["start"], window_time["end"]) 
            and not collected_today[window_name]):
            
            print(f"📊 {{os.path.basename(os.getcwd())}}: COLETANDO SNAPSHOT - Janela {{window_name}} ({{current_hour_min}})")
            
            # REALIZAR COLETA
            success = GrowthCommands.save_now(twb_instance)
            
            if success:
                collected_today[window_name] = True
                snapshots_hoje = sum(1 for k in ["morning", "afternoon", "evening"] 
                                   if collected_today[k])
                print(f"✅ {{os.path.basename(os.getcwd())}}: Snapshot {{snapshots_hoje}}/3 coletado!")
            break

# ==========================================
# FIM DO SISTEMA DE CRESCIMENTO
# ==========================================

def main():
    """Função principal do launcher"""
    try:
        # 1. Configurar contexto da conta (DEVE ser primeiro)
        account_name, account_dir = setup_account_context()
        
        # 2. Verificar arquivos essenciais
        if not verify_account_files(account_dir):
            return
        
        # 3. Importar e executar o TWB (agora com contexto definido)
        import twb
        twb.main()
        
    except ImportError as e:
        print(f"Erro de importação: {{e}}")
        print("Verifique se a TWB_Library está no local correto")
        import traceback
        traceback.print_exc()
    except KeyboardInterrupt:
        print("Execução interrompida pelo usuário")
    except Exception as e:
        print(f"Erro inesperado: {{e}}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
'''
    
    launcher_file = account_dir / "run.py"
    with open(launcher_file, 'w', encoding='utf-8') as f:
        f.write(launcher_content)
    
    print(f"Launcher criado: {launcher_file}")
    
    # Script batch para Windows
    batch_content = f'''@echo off
title TWB - {account_name}
cd /d "{account_dir}"
echo Iniciando TWB para {account_name}...
echo Diretorio: %CD%
echo.
python run.py
echo.
echo Pressione qualquer tecla para fechar...
pause
'''
    
    batch_file = account_dir / "start.bat"
    with open(batch_file, 'w', encoding='utf-8') as f:
        f.write(batch_content)
    
    print(f"Script batch criado: {batch_file}")
    
    # Instruções finais
    print("-" * 60)
    print(f"Conta '{account_name}' configurada com sucesso!")
    print("-" * 60)
    print("\nESTRUTURA CRIADA:")
    print(f"├── {account_dir}/")
    print(f"│   ├── config.json        (configuração isolada)")
    print(f"│   ├── attacks.json       (ataques isolados)")
    print(f"│   ├── run.py            (launcher com contexto)")
    print(f"│   ├── start.bat         (script Windows)")
    print(f"│   └── cache/            (cache isolado)")
    print(f"│       ├── session.json  (sessão isolada)")
    print(f"│       ├── attacks/")
    print(f"│       ├── reports/")
    print(f"│       ├── villages/")
    print(f"│       └── managed/")
    print("\nCOMO EXECUTAR:")
    print(f"1. python manager_geral.py run {account_name}")
    print(f"2. cd {account_dir} && python run.py")
    print(f"3. Executar {batch_file} (Windows)")
    print("\nPRÓXIMOS PASSOS:")
    print(f"1. Execute: python manager_geral.py run {account_name}")
    print("2. O bot pedirá o cookie do navegador na primeira execução")
    print("3. O session.json será criado automaticamente")
    print(f"4. Edite configurações em: {config_file}")
    print("\nIMPORTANTE:")
    print("- O run.py agora configura contexto ANTES de importar TWB")
    print("- Cada conta usa arquivos completamente isolados")
    print("- Session.json será criado automaticamente quando fornecido o cookie")
    print("- Cache, config e attacks são independentes entre contas")
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("TWB Multi-Contas - Setup de Nova Conta")
        print("-" * 50)
        print("Uso: python setup_account.py <nome_da_conta> [config_base]")
        print("\nExemplos:")
        print("  python setup_account.py jogador_pvp")
        print("  python setup_account.py conta_farm accounts/conta1/config.json")
        print("\nDica: Use o nome do jogador no Tribal Wars como nome da conta")
        print("\nO que será criado:")
        print("- Estrutura isolada de cache")
        print("- Config.json específico da conta")
        print("- Launcher run.py com contexto correto")
        print("- Session.json isolado")
        print("- Script start.bat para Windows")
        sys.exit(1)
    
    account_name = sys.argv[1]
    base_config = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = setup_account(account_name, base_config)
    
    if success:
        print(f"\nSetup completo! A conta '{account_name}' está pronta para uso.")
        print(f"Execute: python manager_geral.py run {account_name}")
    else:
        print(f"\nErro durante o setup da conta '{account_name}'.")