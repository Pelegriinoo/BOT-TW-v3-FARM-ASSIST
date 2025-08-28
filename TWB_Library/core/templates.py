"""
Manages template files
"""
import os
from pathlib import Path
from core.filemanager import FileManager


class TemplateManager:
    """
    Template manager file
    """
    @staticmethod
    def get_template(category, template="basic", output_json=False):
        """
        Reads a specific text file with arguments
        TODO: switch to improved FileManager
        """
        # Os templates ficam sempre na biblioteca principal, não na conta específica
        library_root = Path(os.path.dirname(__file__)).parent
        template_path = library_root / "templates" / category / f"{template}.txt"
        
        #print(f"[DEBUG] Trying to load template: {template_path}")
        
        if not template_path.exists():
            print(f"[ERROR] Template file not found: {template_path}")
            return None
            
        if output_json:
            # Para JSON, usar o FileManager mas com caminho absoluto
            try:
                with open(template_path, 'r', encoding='utf-8') as file:
                    import json
                    return json.load(file)
            except Exception as e:
                print(f"[ERROR] Error reading JSON template {template_path}: {e}")
                return None
        
        # Para arquivos de texto, ler diretamente
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                content = file.read()
                if not content or content.strip() == "":
                    print(f"[WARNING] Template file is empty: {template_path}")
                    return []
                result = content.strip().split()
                print(f"[SUCCESS] Loaded template {template_path} with {len(result)} items")
                return result
        except Exception as e:
            print(f"[ERROR] Error reading template {template_path}: {e}")
            return None
