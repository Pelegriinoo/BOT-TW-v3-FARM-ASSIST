import asyncio
import time
import telegram

from core.filemanager import FileManager
from core.exceptions import InvalidJSONException


class _Notification:
    bot = None
    enabled = False
    channel_id = None
    token = None
    bot_name = None
    last_message_time = 0
    message_delay = 7200  # 2 horas em segundos (2 * 60 * 60 = 7200)

    def __init__(self):
        self.get_config()

        if self.enabled:
            self.loop = asyncio.new_event_loop()
            self.bot = telegram.Bot(token=self.token)

    def get_config(self):
        try:
            # Usa FileManager que já tem suporte ao contexto multi-contas
            config = FileManager.load_json_file("config.json")
        except InvalidJSONException:
            config = None
            self.enabled = False
        except Exception:
            config = None
            self.enabled = False
            
        if config:
            notification_config = config.get("notifications", {})
            self.enabled = notification_config.get("enabled", False)
            self.channel_id = notification_config.get("channel_id")
            self.token = notification_config.get("token")
            self.bot_name = notification_config.get("bot_name", "TWB Bot")
            
            # Configura delay personalizado se especificado no config
            self.message_delay = notification_config.get("message_delay_seconds", 7200)
            
            print(f"[Notification] Delay configurado: {self.message_delay/3600:.1f} horas entre mensagens")

    def _should_send_message(self, force=False):
        """
        Verifica se deve enviar mensagem baseado no delay configurado
        force=True para mensagens críticas (CAPTCHA, erros graves)
        """
        if force:
            return True
            
        current_time = time.time()
        time_since_last = current_time - self.last_message_time
        
        if time_since_last >= self.message_delay:
            return True
        
        # Log quando mensagem é bloqueada por rate limit
        remaining_time = self.message_delay - time_since_last
        remaining_minutes = remaining_time / 60
        print(f"[Notification] Mensagem bloqueada - aguarde {remaining_minutes:.1f} minutos")
        return False

    def send(self, message, force=False):
        """
        Envia mensagem com sistema de rate limiting
        force=True para mensagens críticas que devem sempre ser enviadas
        """
        if not self.enabled or not self.bot:
            return

        # Verifica rate limit (exceto para mensagens forçadas)
        if not self._should_send_message(force):
            return

        try:
            # Atualiza o bot_name se necessário
            self._update_bot_name_if_needed()
            
            # Limpar caracteres especiais do Markdown que podem causar erro
            clean_message = self._clean_markdown(message)
            
            # Add bot identifier to message
            formatted_message = f"{self.bot_name}\n{clean_message}"
            
            task = self.loop.create_task(self.send_async(formatted_message))
            self.loop.run_until_complete(task)
            
            # Atualiza timestamp da última mensagem apenas se enviou com sucesso
            self.last_message_time = time.time()
            
            if not force:
                print(f"[Notification] Mensagem enviada - próxima em {self.message_delay/3600:.1f} horas")
            else:
                print(f"[Notification] Mensagem crítica enviada")
                
        except Exception as e:
            # Se erro no Telegram, não quebrar o bot
            print(f"[Notification] Erro ao enviar: {e}")

    def send_critical(self, message):
        """
        Envia mensagem crítica que ignora rate limiting
        Para CAPTCHA, erros graves, etc.
        """
        self.send(message, force=True)

    def _update_bot_name_if_needed(self):
        """
        Atualiza o bot_name se ainda contém placeholder
        """
        try:
            placeholders_to_check = ["{NOME_DA_CONTA}", "{nome_conta_tw}", "{server}"]
            has_placeholder = any(placeholder in self.bot_name for placeholder in placeholders_to_check)
            
            if has_placeholder or self.bot_name == "TWB Bot":
                # Tenta carregar o config usando FileManager (contexto multi-contas)
                config = FileManager.load_json_file("config.json")
                if config:
                    updated_name = config.get("notifications", {}).get("bot_name", self.bot_name)
                    if updated_name != self.bot_name and not any(placeholder in updated_name for placeholder in placeholders_to_check):
                        self.bot_name = updated_name
                        print(f"[Notification] Nome do bot atualizado para: {self.bot_name}")
        except Exception as e:
            print(f"[Notification] Erro ao atualizar nome do bot: {e}")

    def _clean_markdown(self, message):
        """Remove ou escapa caracteres problemáticos do Markdown"""
        # Remove emojis que podem causar problemas de parsing
        clean_message = message.replace("🚀", "🚀 ")
        
        # Escapa caracteres especiais do Markdown
        special_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            clean_message = clean_message.replace(char, f"\\{char}")
        
        return clean_message

    async def send_async(self, message):
        try:
            # Tentar enviar com Markdown
            await self.bot.send_message(chat_id=self.channel_id, text=message, parse_mode='Markdown')
        except telegram.error.BadRequest:
            try:
                # Se falhar, tentar sem Markdown
                await self.bot.send_message(chat_id=self.channel_id, text=message, parse_mode=None)
            except Exception as e:
                print(f"[Notification] Falha total ao enviar: {e}")


Notification = _Notification()