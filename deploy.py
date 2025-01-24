#!/usr/bin/env python3
import os
import sys
import logging
import subprocess
from pathlib import Path
import psutil
import json
from datetime import datetime
import signal
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Always log to stdout
    ]
)

# Try to set up file logging, but don't fail if it's not possible
try:
    Path("logs").mkdir(exist_ok=True)
    file_handler = logging.FileHandler('logs/bot.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
except Exception as e:
    logging.warning(f"Could not set up file logging: {e}")

logger = logging.getLogger(__name__)

class BotDeployment:
    def __init__(self):
        self.bot_process = None
        self.monitor_interval = 60  # Check every minute
        self.max_memory_percent = 80
        self.max_cpu_percent = 80
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create necessary directories."""
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        Path("data/analytics").mkdir(exist_ok=True)
        Path("cache").mkdir(exist_ok=True)
    
    def check_system_resources(self):
        """Check system resources and log warnings if necessary."""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        
        if memory.percent > self.max_memory_percent:
            logger.warning(f"High memory usage: {memory.percent}%")
        
        if cpu > self.max_cpu_percent:
            logger.warning(f"High CPU usage: {cpu}%")
        
        return memory.percent < self.max_memory_percent and cpu < self.max_cpu_percent
    
    def start_bot(self):
        """Start the bot process."""
        try:
            self.bot_process = subprocess.Popen(
                [sys.executable, "bot.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Bot started with PID: {self.bot_process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False
    
    def stop_bot(self):
        """Stop the bot process."""
        if self.bot_process:
            self.bot_process.terminate()
            try:
                self.bot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.bot_process.kill()
            logger.info("Bot stopped")
    
    def restart_bot(self):
        """Restart the bot process."""
        logger.info("Restarting bot...")
        self.stop_bot()
        return self.start_bot()
    
    def monitor_bot(self):
        """Monitor bot process and system resources."""
        while True:
            try:
                # Check if process is running
                if self.bot_process and self.bot_process.poll() is not None:
                    logger.error("Bot process died, restarting...")
                    self.restart_bot()
                
                # Check system resources
                if not self.check_system_resources():
                    logger.warning("System resources critical, attempting restart...")
                    self.restart_bot()
                
                # Log current stats
                self.log_stats()
                
            except Exception as e:
                logger.error(f"Error in monitor_bot: {e}")
            
            # Sleep for monitor interval
            time.sleep(self.monitor_interval)
    
    def log_stats(self):
        """Log current system and bot statistics."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "memory_usage": psutil.virtual_memory().percent,
            "cpu_usage": psutil.cpu_percent(),
            "disk_usage": psutil.disk_usage('/').percent,
        }
        
        with open(f"logs/stats_{datetime.now().strftime('%Y-%m-%d')}.json", 'a') as f:
            json.dump(stats, f)
            f.write('\n')
    
    def handle_signal(self, signum, frame):
        """Handle system signals."""
        logger.info(f"Received signal {signum}")
        if signum in (signal.SIGTERM, signal.SIGINT):
            logger.info("Shutting down gracefully...")
            self.stop_bot()
            sys.exit(0)

def main():
    deployment = BotDeployment()
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, deployment.handle_signal)
    signal.signal(signal.SIGINT, deployment.handle_signal)
    
    logger.info("Starting bot deployment...")
    if deployment.start_bot():
        try:
            deployment.monitor_bot()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            deployment.stop_bot()
    else:
        logger.error("Failed to start bot")
        sys.exit(1)

if __name__ == "__main__":
    main() 