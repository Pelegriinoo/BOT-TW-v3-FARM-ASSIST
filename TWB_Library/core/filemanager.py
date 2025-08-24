import json
import os
from pathlib import Path

from core.exceptions import InvalidJSONException, FileNotFoundException
from core.context import AccountContext


class FileManager:
    """Provides methods for file and directory management with multi-account support."""

    @staticmethod
    def get_root():
        """Returns the root directory for the current account context."""
        if AccountContext.is_multi_account_mode():
            return AccountContext.get_account_path()
        # Fallback para compatibilidade com sistema antigo
        return Path(os.path.dirname(__file__)).parent

    @staticmethod
    def get_path(path):
        """Returns the full path of a file or directory in the current account context."""
        root = FileManager.get_root()
        return root / path

    @staticmethod
    def path_exists(path):
        """Returns True if the path exists, False otherwise."""
        if isinstance(path, str):
            if AccountContext.is_multi_account_mode():
                # Para modo multi-conta, usar caminho relativo à conta
                full_path = FileManager.get_path(path)
            else:
                # Para modo legado, manter comportamento original
                full_path = Path(path) if not Path(path).is_absolute() else Path(path)
        else:
            full_path = Path(path)
        
        return full_path.exists()

    @staticmethod
    def create_directory(directory):
        """Creates a directory if it does not exist."""
        Path(directory).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_directories(directories):
        """Creates a list of directories in the root directory if they do not exist."""
        root_directory = FileManager.get_root()
        for directory in directories:
            directory_path = root_directory / directory
            FileManager.create_directory(directory_path)

    @staticmethod
    def list_directory(directory, ends_with=None):
        """Returns a list of files in a directory."""
        full_path = FileManager.get_path(directory)
        
        if not full_path.exists():
            return []
            
        files = [f.name for f in full_path.iterdir() if f.is_file()]
        
        if ends_with:
            files = [f for f in files if f.endswith(ends_with)]
        return files

    @staticmethod
    def __open_file(path, mode="r"):
        """Opens a file in the specified mode. Private do NOT use outside filemanager."""
        if isinstance(path, str):
            full_path = FileManager.get_path(path)
        else:
            full_path = Path(path)
            
        try:
            return open(full_path, mode, encoding='utf-8')
        except Exception:
            raise FileNotFoundException

    @staticmethod
    def read_file(path):
        """Reads the contents of a file and returns the data. Returns None if the file does not exist."""
        full_path = FileManager.get_path(path)

        if not full_path.exists():
            return None

        with FileManager.__open_file(path) as file:
            return file.read()

    @staticmethod
    def read_lines(path):
        """Reads the contents of a file and returns the lines. Returns None if the file does not exist."""
        full_path = FileManager.get_path(path)

        if not full_path.exists():
            return None

        with FileManager.__open_file(path) as file:
            return file.readlines()

    @staticmethod
    def remove_file(path):
        """Removes a file if it exists."""
        full_path = FileManager.get_path(path)

        if full_path.exists():
            full_path.unlink()

    @staticmethod
    def load_json_file(path, **kwargs):
        """Loads a JSON file and returns the data. Returns None if the file does not exist."""
        full_path = FileManager.get_path(path)

        if not full_path.exists():
            return None

        with FileManager.__open_file(path) as file:
            try:
                return json.load(file, **kwargs)
            except json.decoder.JSONDecodeError:
                raise InvalidJSONException

    @staticmethod
    def save_json_file(data, path, **kwargs):
        """Saves data to a JSON file. If the file does not exist, it will be created."""
        # Garantir que o diretório pai existe
        full_path = FileManager.get_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with FileManager.__open_file(path, mode="w") as file:
            json.dump(data, file, indent=2, sort_keys=False, ensure_ascii=False, **kwargs)

    @staticmethod
    def copy_file(src_path, dest_path):
        """Copies a file from the source path to the destination path."""
        full_src_path = FileManager.get_path(src_path)
        full_dest_path = FileManager.get_path(dest_path)

        if not full_src_path.exists():
            return False

        # Garantir que o diretório de destino existe
        full_dest_path.parent.mkdir(parents=True, exist_ok=True)

        with FileManager.__open_file(src_path) as src_file:
            with FileManager.__open_file(dest_path, mode="w") as dest_file:
                dest_file.write(src_file.read())