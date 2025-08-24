#!/usr/bin/env python3
"""
TWB Multi-Contas - Sistema de Gerenciamento
Inicialização rápida para o sistema organizacional com configuração inteligente
"""
import sys
import json
from pathlib import Path

# Adiciona o diretório atual ao path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def extract_config_from_url(url):
    """
    Extrai server e endpoint da URL da vila
    """
    import re
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url)
        
        # Extrai código do servidor (br136, pt94, etc.)
        server_match = re.match(r'([a-z]+\d+)\.', parsed.netloc)
        if not server_match:
            return None, "Não foi possível identificar o servidor na URL"
        
        server_code = server_match.group(1)
        
        # Monta endpoint (só até game.php)
        endpoint = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Valida se é URL válida do jogo
        if "game.php" not in endpoint:
            return None, "URL deve conter 'game.php'"
        
        result = {
            'server': server_code,
            'endpoint': endpoint
        }
        
        return result, None
        
    except Exception as e:
        return None, f"Erro ao processar URL: {e}"

def guess_endpoint_url(server_code):
    """
    Adivinha URL baseada no código do servidor
    """
    server_patterns = {
        'br': 'tribalwars.com.br',
        'pt': 'tribalwars.com.pt',
        'en': 'tribalwars.net',
        'nl': 'tribalwars.nl',
        'de': 'die-staemme.de',
        'fr': 'guerretribale.fr',
        'it': 'tribals.it',
        'es': 'guerrastribales.es'
    }
    
    import re
    match = re.match(r'([a-z]+)', server_code.lower())
    if match:
        prefix = match.group(1)
        domain = server_patterns.get(prefix)
        if domain:
            return f"https://{server_code}.{domain}/game.php"
    
    return None

def manual_server_config(config):
    """
    Configuração manual do servidor (fallback)
    """
    print("\n🔧 Configuração manual:")
    
    print("\n1️⃣ Código do servidor:")
    print("   Exemplos: br136, br137, pt94, en115")
    server_code = input("   Digite o código> ").strip().lower()
    
    if not server_code:
        print("Código obrigatório!")
        return None
    
    config["server"]["server"] = server_code
    
    print(f"\n2️⃣ URL do jogo:")
    suggested_url = guess_endpoint_url(server_code)
    if suggested_url:
        print(f"   Sugestão: {suggested_url}")
        use_suggestion = input("   Usar esta URL? [S/n]> ").strip().lower()
        
        if use_suggestion in ['', 's', 'sim', 'y', 'yes']:
            endpoint_url = suggested_url
        else:
            endpoint_url = input("   Digite a URL completa> ").strip()
    else:
        endpoint_url = input("   Digite a URL completa> ").strip()
    
    if not endpoint_url or "game.php" not in endpoint_url:
        print("URL inválida!")
        return None
    
    config["server"]["endpoint"] = endpoint_url
    return config

def setup_telegram_config(config):
    """
    Configuração do Telegram
    """
    print("\n Configuração do Telegram:")
    print("1. Crie um bot: envie /newbot para @BotFather")
    print("2. Obtenha o ID do chat: use @userinfobot")
    
    token = input("\nToken do bot> ").strip()
    if not token or ":" not in token:
        print("  Token inválido, pulando Telegram")
        return config
    
    channel_id = input("📝 ID do chat/canal> ").strip()
    if not channel_id:
        print("  ID inválido, pulando Telegram")
        return config
    
    if "notifications" not in config:
        config["notifications"] = {}
    
    config["notifications"]["enabled"] = True
    config["notifications"]["token"] = token
    config["notifications"]["channel_id"] = channel_id
    config["notifications"]["message_delay_seconds"] = 7200
    
    # Bot name com template
    server_code = config.get("server", {}).get("server", "servidor")
    config["notifications"]["bot_name"] = f"TWB {server_code.upper()} - {{NOME_DA_CONTA}}"
    
    print("Telegram configurado!")
    return config

def validate_account_config(account_name):
    """
    Valida e completa configurações de uma conta específica
    """
    from manager_geral import TWBManager
    
    manager = TWBManager()
    account_dir = manager.accounts_dir / account_name
    config_file = account_dir / "config.json"
    
    if not config_file.exists():
        print(f"Conta '{account_name}' não encontrada!")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Erro ao ler config.json: {e}")
        return False
    
    print(f"\n🔍 Validando configuração da conta: {account_name}")
    config_updated = False
    
    # VALIDAÇÃO 1: Server e Endpoint (modo inteligente)
    server_config = config.get("server", {})
    if not server_config.get("server") or not server_config.get("endpoint"):
        print("\n" + "="*60)
        print("🌐 CONFIGURAÇÃO DO SERVIDOR")
        print("="*60)
        print("Escolha uma das opções:")
        print("1️⃣  Colar URL da sua vila (RECOMENDADO)")
        print("2️⃣  Configurar manualmente")
        
        choice = input("\nEscolha [1/2]> ").strip()
        
        if choice == "1":
            print("\n🔗 Cole a URL da sua vila aqui:")
            print("   Vá até o jogo, entre em qualquer vila e copie a URL completa")
            print("   Exemplo: https://br136.tribalwars.com.br/game.php?village=44839&screen=overview")
            
            url = input("\n🔗 Cole a URL aqui> ").strip()
            
            if url:
                extracted, error = extract_config_from_url(url)
                
                if extracted:
                    config["server"]["server"] = extracted['server']
                    config["server"]["endpoint"] = extracted['endpoint']
                    config_updated = True
                    
                    print(f"Extraído automaticamente:")
                    print(f"   • Servidor: {extracted['server']}")
                    print(f"   • Endpoint: {extracted['endpoint']}")
                    print(f"   • Configuração completa!")
                else:
                    print(error)
                    print("  Vamos configurar manualmente...")
                    config = manual_server_config(config)
                    if config is None:
                        return False
                    config_updated = True
            else:
                print("  URL vazia, configurando manualmente...")
                config = manual_server_config(config)
                if config is None:
                    return False
                config_updated = True
        else:
            config = manual_server_config(config)
            if config is None:
                return False
            config_updated = True
    
    # VALIDAÇÃO 2: User Agent (obrigatório)
    bot_config = config.get("bot", {})
    if not bot_config.get("user_agent"):
        print("\n" + "="*60)
        print("🔒 USER AGENT (ANTI-BANIMENTO)")
        print("="*60)
        print("  IMPORTANTE: O User Agent é obrigatório para evitar banimento!")
        print("Isso faz o bot imitar seu navegador real.")
        
        print("\n📋 Como descobrir seu User Agent:")
        print("1. Acesse: https://www.whatismybrowser.com/detect/what-is-my-user-agent")
        print("2. Copie todo o texto que aparece")
        print("3. Cole aqui embaixo")
        
        print("\nDica: Deve começar com 'Mozilla/5.0' e ser bem longo")
        
        user_agent = input("\n🔒 Cole seu User Agent aqui> ").strip()
        
        if not user_agent:
            print("User Agent é obrigatório! O bot não pode continuar sem ele.")
            return False
        
        if len(user_agent) < 50 or not user_agent.startswith("Mozilla"):
            print("  Este User Agent parece inválido ou muito curto.")
            print("Exemplo válido:")
            print("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...")
            
            continue_anyway = input("Continuar mesmo assim? [s/N]> ").strip().lower()
            if continue_anyway not in ['s', 'sim', 'y', 'yes']:
                return False
        
        config["bot"]["user_agent"] = user_agent
        config_updated = True
        print("User Agent configurado!")
    
    # VALIDAÇÃO 3: Telegram (opcional)
    notification_config = config.get("notifications", {})
    if not notification_config.get("enabled"):
        print("\n" + "="*60)
        print(" NOTIFICAÇÕES TELEGRAM (OPCIONAL)")
        print("="*60)
        print("O bot pode te avisar pelo Telegram quando:")
        print("• Detectar CAPTCHA")
        print("•   Sessão expirar")
        print("• Ocorrer erro grave")
        
        setup_telegram = input("\n Configurar Telegram? [s/N]> ").strip().lower()
        
        if setup_telegram in ['s', 'sim', 'y', 'yes']:
            config = setup_telegram_config(config)
            config_updated = True
        else:
            print(" Telegram não configurado (você pode fazer depois)")
    
    # Salva configurações se foram alteradas
    if config_updated:
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"\nConfigurações salvas em {config_file}")
        except Exception as e:
            print(f"Erro ao salvar config.json: {e}")
            return False
    
    return True

def interactive_menu():
    """
    Menu interativo com acesso direto às contas por número
    """
    from manager_geral import TWBManager
    
    manager = TWBManager()
    
    while True:
        print("\n" + "="*50)
        print("TWB MULTI-CONTAS - MENU PRINCIPAL")
        print("="*50)
        
        # Mostra contas disponíveis
        accounts = manager.list_accounts()
        if accounts:
            print("\nContas disponíveis:")
            for i, account in enumerate(accounts, 1):
                print(f"  {i}. {account}")
        else:
            print("\nNenhuma conta configurada")
        
        print("\nOpções:")
        print("a. Configurar conta") 
        print("b. Criar nova conta")
        print("c. Listar todas as contas")
        print("q. Sair")
        
        try:
            choice = input("\nDigite o número da conta OU opção [a/b/c/q]> ").strip().lower()
            
            # Verifica se é número (acesso direto à conta)
            if choice.isdigit():
                account_num = int(choice)
                if 1 <= account_num <= len(accounts):
                    account_name = accounts[account_num - 1]
                    print(f"\nPreparando execução da conta: {account_name}")
                    
                    # Validação automática
                    if validate_account_config(account_name):
                        print(f"\nConfiguração validada! Iniciando bot...")
                        print("-" * 50)
                        try:
                            manager.run_account(account_name)
                        except KeyboardInterrupt:
                            print("\nExecução interrompida pelo usuário")
                        except Exception as e:
                            print(f"\nErro durante execução: {e}")
                    else:
                        print(f"\nNão foi possível executar a conta '{account_name}'")
                        print("Configure os dados obrigatórios primeiro (opção 'a')")
                else:
                    print(f"Número inválido! Escolha entre 1-{len(accounts)}")
            
            elif choice == "a":
                # Configurar conta
                if not accounts:
                    print("ERRO: Nenhuma conta disponível para configurar!")
                    continue
                
                print("\nCONFIGURAR CONTA:")
                print("Contas disponíveis:")
                for i, account in enumerate(accounts, 1):
                    print(f"  {i}. {account}")
                
                account_choice = input("Digite o número da conta> ").strip()
                
                if account_choice.isdigit():
                    account_num = int(account_choice)
                    if 1 <= account_num <= len(accounts):
                        account_name = accounts[account_num - 1]
                        print(f"\nConfigurando conta: {account_name}")
                        validate_account_config(account_name)
                    else:
                        print(f"Número inválido! Escolha entre 1-{len(accounts)}")
                else:
                    print("Digite apenas o número da conta!")
                
            elif choice == "b":
                # Criar nova conta
                print("\nCRIAR NOVA CONTA:")
                account_name = input("Digite o nome da nova conta> ").strip()
                
                if not account_name:
                    print("ERRO: Nome da conta não pode estar vazio!")
                    continue
                
                if account_name in accounts:
                    print(f"ERRO: Conta '{account_name}' já existe!")
                    continue
                
                try:
                    from setup_account import setup_account
                    setup_account(account_name)
                    print(f"Conta '{account_name}' criada com sucesso!")
                except Exception as e:
                    print(f"Erro ao criar conta: {e}")
                
            elif choice == "c":
                # Listar contas
                print("\nTODAS AS CONTAS:")
                if accounts:
                    for i, account in enumerate(accounts, 1):
                        print(f"  {i}. {account}")
                        
                        # Mostra status da configuração
                        try:
                            account_dir = manager.accounts_dir / account
                            config_file = account_dir / "config.json"
                            
                            if config_file.exists():
                                with open(config_file, 'r', encoding='utf-8') as f:
                                    config = json.load(f)
                                
                                server = config.get("server", {}).get("server", "FALTA")
                                user_agent = "OK" if config.get("bot", {}).get("user_agent") else "FALTA"
                                telegram = "OK" if config.get("notifications", {}).get("enabled") else "FALTA"
                                
                                print(f"     Servidor: {server} | User Agent: {user_agent} | Telegram: {telegram}")
                            else:
                                print("     Config não encontrado")
                        except:
                            print("     Erro ao ler config")
                else:
                    print("  Nenhuma conta configurada")
                
            elif choice == "q":
                # Sair
                print("\nTchau!")
                break
                
            else:
                print("Opção inválida! Digite um número da conta ou letra da opção [a/b/c/q]")
                
        except KeyboardInterrupt:
            print("\n\nSaindo...")
            break
        except Exception as e:
            print(f"\nErro inesperado: {e}")

def main():
    print("TWB Multi-Contas - Sistema de Gerenciamento")
    print("-" * 50)
    
    try:
        from manager_geral import TWBManager
        
        if len(sys.argv) > 1:
            # Modo linha de comando
            command = sys.argv[1]
            
            manager = TWBManager()
            
            if command == "list":
                accounts = manager.list_accounts()
                if accounts:
                    print("Contas disponíveis:")
                    for i, account in enumerate(accounts, 1):
                        print(f"  {i}. {account}")
                else:
                    print("Nenhuma conta configurada")
                    
            elif command == "run" and len(sys.argv) > 2:
                account_name = sys.argv[2]
                print(f"\n🚀 Preparando execução da conta: {account_name}")
                
                # VALIDAÇÃO AUTOMÁTICA antes de executar
                if validate_account_config(account_name):
                    print(f"\nConfiguração validada! Iniciando bot...")
                    print("-" * 50)
                    manager.run_account(account_name)
                else:
                    print(f"\nNão foi possível executar a conta '{account_name}'")
                    print("Configure os dados obrigatórios e tente novamente.")
                
            elif command == "create" and len(sys.argv) > 2:
                from setup_account import setup_account
                base_config = sys.argv[3] if len(sys.argv) > 3 else None
                setup_account(sys.argv[2], base_config)
                
            elif command == "config" and len(sys.argv) > 2:
                # Comando para reconfigurar uma conta
                account_name = sys.argv[2]
                print(f"\n⚙️  Reconfigurando conta: {account_name}")
                validate_account_config(account_name)
                
            else:
                show_usage()
        else:
            # Modo interativo melhorado
            interactive_menu()
            
    except ImportError as e:
        print(f"Erro de importação: {e}")
        print("Verifique se todos os arquivos estão no local correto")
    except KeyboardInterrupt:
        print("\nSistema encerrado pelo usuário")
    except Exception as e:
        print(f"Erro inesperado: {e}")

def show_usage():
    print("Uso:")
    print("  python start.py                    # Menu interativo")
    print("  python start.py list               # Listar contas")
    print("  python start.py run <conta>        # Executar conta (com validação automática)")
    print("  python start.py config <conta>     # Reconfigurar conta")
    print("  python start.py create <conta>     # Criar nova conta")
    print()
    print("🎯 NOVO: Configuração inteligente!")
    print("• Cole URL da vila para configurar automaticamente")
    print("• Validação obrigatória de User Agent")
    print("• Setup opcional do Telegram")
    print()
    print("Estrutura do projeto:")
    print("  UNIFICACAO/")
    print("  ├── TWB_Library/          # Biblioteca compartilhada")
    print("  ├── accounts/             # Contas isoladas")
    print("  │   ├── conta1_motumbo/")
    print("  │   └── conta2_exemplo/")
    print("  ├── manager_geral.py      # Gerenciador principal")
    print("  ├── setup_account.py      # Setup de novas contas")
    print("  └── start.py             # Este arquivo")

if __name__ == "__main__":
    main()
