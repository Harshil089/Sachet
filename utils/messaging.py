"""
Utility functions for sending alerts via Telegram and Discord
"""
import asyncio
import requests
import os

def send_telegram_alert(message, photo_url=None, bot_token=None, chat_id=None):
    """
    Send alert via Telegram bot (synchronous wrapper)
    
    Args:
        message: Text message to send
        photo_url: Optional photo URL to attach
        bot_token: Telegram bot token (from env if not provided)
        chat_id: Telegram chat ID (from env if not provided)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        return asyncio.run(_send_telegram_alert_async(message, photo_url, bot_token, chat_id))
    except Exception as e:
        print(f"❌ Telegram alert error: {str(e)}")
        return False


async def _send_telegram_alert_async(message, photo_url=None, bot_token=None, chat_id=None):
    """
    Send alert via Telegram bot (async)
    """
    try:
        from telegram import Bot
        
        token = bot_token or os.environ.get('TELEGRAM_BOT_TOKEN')
        chat = chat_id or os.environ.get('TELEGRAM_CHAT_ID')
        
        if not token or not chat:
            print("⚠️ Telegram not configured (missing token or chat_id)")
            return False
        
        bot = Bot(token=token)
        
        if photo_url:
            await bot.send_photo(chat_id=chat, photo=photo_url, caption=message)
        else:
            await bot.send_message(chat_id=chat, text=message)
        
        print(f"✅ Telegram alert sent to chat {chat}")
        return True
        
    except ImportError:
        print("⚠️ python-telegram-bot not installed")
        return False
    except Exception as e:
        print(f"❌ Telegram send error: {str(e)}")
        return False


def send_discord_alert(message, photo_url=None, webhook_url=None):
    """
    Send alert via Discord webhook
    
    Args:
        message: Text message to send
        photo_url: Optional photo URL to attach
        webhook_url: Discord webhook URL (from env if not provided)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        url = webhook_url or os.environ.get('DISCORD_WEBHOOK_URL')
        
        if not url:
            print("⚠️ Discord not configured (missing webhook URL)")
            return False
        
        payload = {
            "content": message,
        }
        
        if photo_url:
            payload["embeds"] = [{
                "image": {"url": photo_url}
            }]
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 204:
            print(f"✅ Discord alert sent")
            return True
        else:
            print(f"❌ Discord webhook failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Discord alert error: {str(e)}")
        return False


def broadcast_alert(message, photo_url=None, sms_func=None):
    """
    Send alerts via all configured channels (SMS, Telegram, Discord)
    
    Args:
        message: Text message to send
        photo_url: Optional photo URL to attach
        sms_func: Optional SMS sending function
    
    Returns:
        dict: Results from each channel
    """
    results = {
        'telegram': send_telegram_alert(message, photo_url),
        'discord': send_discord_alert(message, photo_url),
        'sms': False
    }
    
    # Send SMS if function provided
    if sms_func:
        try:
            sms_count = sms_func(message)
            results['sms'] = sms_count > 0
        except Exception as e:
            print(f"❌ SMS broadcast error: {str(e)}")
    
    # Log summary
    successful = sum(1 for v in results.values() if v)
    print(f"📢 Alert broadcast: {successful}/{len(results)} channels successful")
    
    return results
