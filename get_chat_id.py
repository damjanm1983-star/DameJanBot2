#!/usr/bin/env python3
"""
Script to help get your Telegram Chat ID
"""

import requests
import time
import sys

BOT_TOKEN = "8619307561:AAEuopebkFEKGeyv2wbjcyWCgY7ANTWJ27Y"

def get_updates():
    """Get updates from Telegram bot"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('ok') and data.get('result'):
            print("\n✅ Found messages! Here are your Chat IDs:\n")
            seen_chats = set()
            
            for update in data['result']:
                if 'message' in update:
                    chat = update['message']['chat']
                    chat_id = chat['id']
                    
                    if chat_id not in seen_chats:
                        seen_chats.add(chat_id)
                        chat_type = chat.get('type', 'unknown')
                        
                        if chat_type == 'private':
                            name = f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
                            print(f"👤 Personal Chat:")
                            print(f"   Name: {name}")
                            print(f"   Chat ID: {chat_id}")
                        elif chat_type in ['group', 'supergroup']:
                            print(f"👥 Group Chat:")
                            print(f"   Name: {chat.get('title', 'Unknown')}")
                            print(f"   Chat ID: {chat_id}")
                        elif chat_type == 'channel':
                            print(f"📢 Channel:")
                            print(f"   Name: {chat.get('title', 'Unknown')}")
                            print(f"   Chat ID: {chat_id}")
                        
                        print()
            
            if not seen_chats:
                print("⚠️  No messages found yet.")
                print("   Please send a message to your bot first!")
                print("   Search for @DamJanBot in Telegram and send 'Hello'")
        else:
            print("\n⚠️  No messages found.")
            print("   Please send a message to your bot first!")
            print("   Search for @DamJanBot in Telegram and send 'Hello'")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def send_test_message(chat_id):
    """Send a test message"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🤖 DamJanBot Test Message\n\nYour bot is working!\nYou'll receive trade notifications here."
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.json().get('ok'):
            print(f"✅ Test message sent successfully!")
            return True
        else:
            print(f"❌ Failed to send message: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 DamJanBot - Telegram Chat ID Finder")
    print("=" * 60)
    print("\n📱 Steps:")
    print("1. Open Telegram")
    print("2. Search for your bot (@DamJanBot)")
    print("3. Send a message (e.g., 'Hello')")
    print("4. Run this script again")
    print("\n" + "=" * 60)
    
    get_updates()
    
    print("\n" + "=" * 60)
    print("💡 To test your bot:")
    print("   python3 get_chat_id.py test YOUR_CHAT_ID")
    print("=" * 60)
