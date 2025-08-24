#!/usr/bin/env python3
"""
Diagnóstico do Farm Assistant
Verifica se tudo está configurado corretamente
"""

import json
import logging
from TWB_Library.game.farm_assistant import FarmAssistantManager


def diagnose_farm_assistant(wrapper, village_id):
    """
    Executa diagnóstico completo do Farm Assistant
    """
    print("🔍 DIAGNÓSTICO DO FARM ASSISTANT")
    print("=" * 50)
    
    # 1. Verifica se o módulo foi importado corretamente
    try:
        assistant = FarmAssistantManager(
            wrapper=wrapper,
            village_id=village_id,
            troopmanager=None
        )
        print("✅ Módulo FarmAssistantManager importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar módulo: {e}")
        return False
    
    # 2. Verifica acesso à página
    try:
        assistant_page = assistant.load_assistant_page()
        
        if assistant_page and assistant_page.status_code == 200:
            print("✅ Página do assistente acessível")
        else:
            print("❌ Erro ao acessar assistente")
            print("💡 Verifique se tem premium ativo no jogo")
            return False
    except Exception as e:
        print(f"❌ Exceção no acesso: {e}")
        return False
    
    # 3. Verifica templates
    try:
        templates = assistant.extract_templates_from_game(assistant_page.text)
        if templates:
            print(f"✅ Templates encontrados: {len(templates)}")
            for tid, troops in templates.items():
                print(f"   Template {tid}: {troops}")
        else:
            print("❌ Nenhum template configurado")
            print("💡 Configure templates A/B no assistente do jogo")
            print("   URL: game.php?village={}&screen=am_farm".format(village_id))
            return False
    except Exception as e:
        print(f"❌ Erro ao extrair templates: {e}")
        return False
    
    # 4. Verifica alvos
    try:
        targets = assistant.extract_targets_from_assistant(assistant_page.text)
        if targets:
            print(f"✅ Alvos encontrados: {len(targets)}")
            valid = [t for t in targets if t['template_a'] or t['template_b']]
            print(f"   Alvos válidos: {len(valid)}")
            
            # Mostra alguns exemplos
            for i, target in enumerate(valid[:3]):
                print(f"   Exemplo {i+1}: {target['coords']} (distância: {target['distance']})")
        else:
            print("⚠️ Nenhum alvo encontrado")
            print("💡 Isso é normal se não há aldeias para farmar")
    except Exception as e:
        print(f"❌ Erro ao extrair alvos: {e}")
        return False
    
    # 5. Teste de validação
    try:
        validation_result = assistant.validate_assistant_access()
        if validation_result:
            print("✅ Validação do assistente bem-sucedida")
        else:
            print("❌ Falha na validação do assistente")
            return False
    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        return False
    
    print()
    print("🎉 DIAGNÓSTICO CONCLUÍDO COM SUCESSO!")
    print("✅ O Farm Assistant está pronto para uso")
    print()
    print("📋 PRÓXIMOS PASSOS:")
    print("1. Ative o assistente em config.json: 'use_assistant': true")
    print("2. Configure templates A/B no jogo se ainda não fez")
    print("3. Teste com uma aldeia primeiro")
    print("4. Monitore os logs para verificar o funcionamento")
    
    return True


def check_config_file():
    """
    Verifica se o arquivo de configuração tem as opções do assistente
    """
    print("\n🔧 VERIFICANDO CONFIGURAÇÃO...")
    
    try:
        # Verifica config.example.json
        with open('config.example.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        if 'use_assistant' in config.get('farms', {}):
            print("✅ config.example.json atualizado com Farm Assistant")
        else:
            print("❌ config.example.json precisa ser atualizado")
            return False
            
        # Verifica se há assistant_settings
        if 'assistant_settings' in config.get('farms', {}):
            print("✅ Configurações avançadas do assistente presentes")
        else:
            print("⚠️ Configurações avançadas opcionais não encontradas")
            
        return True
        
    except FileNotFoundError:
        print("❌ config.example.json não encontrado")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao ler config.example.json: {e}")
        return False


if __name__ == "__main__":
    print("🚀 DIAGNÓSTICO COMPLETO DO FARM ASSISTANT")
    print("=" * 60)
    
    # Verifica configuração
    config_ok = check_config_file()
    
    if config_ok:
        print("\n💡 Para executar diagnóstico completo:")
        print("1. Inicie o bot normalmente")
        print("2. Execute: diagnose_farm_assistant(wrapper, village_id)")
        print("3. Onde wrapper é sua instância de TwClient e village_id é o ID da aldeia")
        
        print("\n📝 EXEMPLO DE USO:")
        print("""
# No console Python do bot ou em script:
from diagnostico_farm_assistant import diagnose_farm_assistant

# Substitua pelos valores reais:
wrapper = seu_wrapper_object
village_id = "12345"

# Execute o diagnóstico:
result = diagnose_farm_assistant(wrapper, village_id)

if result:
    print("Tudo OK! Pode ativar o assistente")
else:
    print("Corrija os problemas antes de usar")
""")
    else:
        print("\n❌ Corrija as configurações antes de prosseguir")
