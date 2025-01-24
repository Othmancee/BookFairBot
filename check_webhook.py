import os
import requests

BOT_TOKEN = "7831438453:AAHsy0VR8qg2FUAPoBPE6MQzQDctZqqzgmQ"

def check_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    response = requests.get(url)
    print("Webhook Info:")
    print(response.json())

if __name__ == "__main__":
    check_webhook() 