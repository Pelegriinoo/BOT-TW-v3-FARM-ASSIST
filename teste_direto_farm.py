#!/usr/bin/env python3
"""
Teste direto do Farm Assistant
Execute este com o bot rodando para testar diretamente
"""

import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add TWB_Library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'TWB_Library'))

def test_farm_assistant():
    """
    Teste básico do Farm Assistant
    """
    print("🔍 TESTE DIRETO DO FARM ASSISTANT")
    print("=" * 50)
    
    try:
        from game.farm_assistant import FarmAssistantManager
        print("✅ FarmAssistantManager importado")
    except Exception as e:
        print(f"❌ Erro no import: {e}")
        return False
    
    # Mock básico para teste
    class MockWrapper:
        def __init__(self):
            self.endpoint = "br136.tribalwars.com.br"
            self.last_h = "test123"
        
        def get_url(self, url):
            print(f"🌐 Simulando GET: {url}")
            # Simula resposta da página do assistente
            class MockResponse:
                status_code = 200
                text = """
                <div>am_farm</div>
                <table id="plunder_list">
                    <tr id="village_12345">
                        <td><a href="view=123">(596|525)</a></td>
                        <td>5.2</td>
                    </tr>
                </table>
                <script>
                Accountmanager.farm.templates['t_13120']['light'] = 3;
                Accountmanager.farm.templates['t_13971']['light'] = 5;
                </script>
                """
            return MockResponse()
    
    try:
        # Cria instância de teste
        mock_wrapper = MockWrapper()
        assistant = FarmAssistantManager(
            wrapper=mock_wrapper,
            village_id="53657",
            troopmanager=None
        )
        
        print("✅ FarmAssistantManager criado")
        
        # Testa carregamento da página
        page = assistant.load_assistant_page()
        if page:
            print("✅ Página do assistente carregada")
        else:
            print("❌ Falha ao carregar página")
            return False
        
        # Testa extração de templates
        templates = assistant.extract_templates_from_game(page.text)
        print(f"✅ Templates extraídos: {templates}")
        
        # Testa extração de alvos
        targets = assistant.extract_targets_from_assistant(page.text)
        print(f"✅ Alvos extraídos: {len(targets)}")
        
        print()
        print("🎉 TESTE BÁSICO PASSOU!")
        print("💡 O Farm Assistant parece estar funcionando")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_farm_assistant()
