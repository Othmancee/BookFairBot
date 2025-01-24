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
import pandas as pd
import plotly.express as px
from collections import defaultdict
import threading

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Always log to stdout
    ]
)

# Try to set up file logging with rotation
try:
    from logging.handlers import RotatingFileHandler
    Path("logs").mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        'logs/bot.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
except Exception as e:
    logging.warning(f"Could not set up file logging: {e}")

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)
        # Get absolute path for dashboard
        self.dashboard_path = os.path.abspath("data/dashboard")
        Path(self.dashboard_path).mkdir(exist_ok=True)
        logger.info(f"Dashboard will be available at: {os.path.join(self.dashboard_path, 'dashboard.html')}")
        
    def record_metric(self, metric_name, value):
        timestamp = datetime.now()
        self.metrics[metric_name].append({
            'timestamp': timestamp,
            'value': value
        })
        
    def generate_dashboard(self):
        """Generate HTML dashboard with Plotly graphs."""
        try:
            # Create separate graphs for different metrics
            dashboard_html = ["<html><head><title>Bot Metrics Dashboard</title></head><body>"]
            dashboard_html.append("<h1>Bot Performance Dashboard</h1>")
            
            for metric_name, values in self.metrics.items():
                if not values:
                    continue
                    
                df = pd.DataFrame(values)
                fig = px.line(df, x='timestamp', y='value', title=f'{metric_name} Over Time')
                graph_html = fig.to_html(full_html=False)
                dashboard_html.append(f"<div>{graph_html}</div>")
            
            dashboard_html.append("</body></html>")
            
            # Save dashboard with absolute path
            dashboard_file = os.path.join(self.dashboard_path, "dashboard.html")
            with open(dashboard_file, "w") as f:
                f.write("\n".join(dashboard_html))
                
            logger.info(f"Dashboard updated at: {os.path.abspath(dashboard_file)}")
        except Exception as e:
            logger.error(f"Failed to generate dashboard: {e}")

class BotDeployment:
    def __init__(self):
        self.bot_process = None
        self.monitor_interval = 60  # Check every minute
        self.max_memory_percent = 80
        self.max_cpu_percent = 80
        self.metrics = MetricsCollector()
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create necessary directories."""
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        Path("data/analytics").mkdir(exist_ok=True)
        Path("data/dashboard").mkdir(exist_ok=True)
        Path("cache").mkdir(exist_ok=True)
    
    def check_system_resources(self):
        """Check system resources and log warnings if necessary."""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        
        # Record metrics
        self.metrics.record_metric('memory_usage', memory.percent)
        self.metrics.record_metric('cpu_usage', cpu)
        
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
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            logger.info(f"Bot started with PID: {self.bot_process.pid}")
            
            # Start output monitoring threads
            threading.Thread(target=self._monitor_output, args=(self.bot_process.stdout, "stdout")).start()
            threading.Thread(target=self._monitor_output, args=(self.bot_process.stderr, "stderr")).start()
            
            return True
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False
    
    def _monitor_output(self, pipe, pipe_name):
        """Monitor bot's output streams."""
        for line in pipe:
            line = line.strip()
            if line:
                logger.info(f"Bot {pipe_name}: {line}")
                if "error" in line.lower() or "exception" in line.lower():
                    self.metrics.record_metric('error_count', 1)
    
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
        dashboard_interval = 300  # Generate dashboard every 5 minutes
        last_dashboard_time = time.time()
        
        while True:
            try:
                # Check if process is running
                if self.bot_process and self.bot_process.poll() is not None:
                    logger.error("Bot process died, restarting...")
                    self.metrics.record_metric('restart_count', 1)
                    self.restart_bot()
                
                # Check system resources
                if not self.check_system_resources():
                    logger.warning("System resources critical, attempting restart...")
                    self.restart_bot()
                
                # Log current stats
                self.log_stats()
                
                # Generate dashboard periodically
                if time.time() - last_dashboard_time >= dashboard_interval:
                    self.metrics.generate_dashboard()
                    last_dashboard_time = time.time()
                
            except Exception as e:
                logger.error(f"Error in monitor_bot: {e}")
                self.metrics.record_metric('monitor_error_count', 1)
            
            time.sleep(self.monitor_interval)
    
    def log_stats(self):
        """Log current system and bot statistics."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "memory_usage": psutil.virtual_memory().percent,
            "cpu_usage": psutil.cpu_percent(),
            "disk_usage": psutil.disk_usage('/').percent,
        }
        
        # Record all stats as metrics
        for key, value in stats.items():
            self.metrics.record_metric(key, value)
        
        with open(f"logs/stats_{datetime.now().strftime('%Y-%m-%d')}.json", 'a') as f:
            json.dump(stats, f)
            f.write('\n')
    
    def handle_signal(self, signum, frame):
        """Handle system signals."""
        logger.info(f"Received signal {signum}")
        if signum in (signal.SIGTERM, signal.SIGINT):
            logger.info("Shutting down gracefully...")
            self.stop_bot()
            # Generate final dashboard
            self.metrics.generate_dashboard()
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
            # Generate final dashboard
            deployment.metrics.generate_dashboard()
    else:
        logger.error("Failed to start bot")
        sys.exit(1)

if __name__ == "__main__":
    main() 