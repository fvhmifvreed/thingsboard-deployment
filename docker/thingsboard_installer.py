#!/usr/bin/env python3

import os
import subprocess
import getpass
import random
import string
import logging
import psutil
import time
import requests
import smtplib
from email.mime.text import MIMEText
from termcolor import colored

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def run_command(command, description=""):
    """Run a shell command and handle errors."""
    logger.info(description)
    try:
        subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute: {command}")
        logger.error(e.stderr.decode())
        exit(1)

def pre_install_check():
    """Check system resources and prerequisites."""
    logger.info("Performing pre-installation checks...")
    
    # Memory check
    mem = psutil.virtual_memory().total / (1024 ** 3)
    if mem < 2:
        logger.warning(f"[WARNING] Available memory is {mem:.2f} GB. Minimum 2GB recommended.")
    
    # Disk space check
    disk = psutil.disk_usage('/').free / (1024 ** 3)
    if disk < 10:
        logger.warning(f"[WARNING] Available disk space is {disk:.2f} GB. Minimum 10GB recommended.")
    
    # Docker check
    if subprocess.run("docker --version", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        logger.info("[INFO] Docker is already installed.")
    else:
        logger.info("[INFO] Docker is not installed. It will be installed.")

def update_and_upgrade_system():
    """Update and upgrade Ubuntu to the latest version."""
    run_command("sudo apt update && sudo apt upgrade -y", "Updating and upgrading Ubuntu")

def install_docker():
    """Install Docker and create Docker group."""
    run_command("sudo apt install -y docker.io", "Installing Docker")
    run_command("sudo systemctl start docker && sudo systemctl enable docker", "Starting and enabling Docker service")
    run_command("sudo groupadd docker || true", "Creating Docker group (if not exists)")
    run_command(f"sudo usermod -aG docker {getpass.getuser()}", "Adding current user to Docker group")

def create_thingsboard_user():
    """Create ThingsBoard user and allow the user to set a secure password."""
    username = "thingsboard_user"
    password = getpass.getpass("[PROMPT] Enter password for ThingsBoard user: ")
    print(f"\n[INFO] ThingsBoard credentials:\nUsername: {username}")
    return username, password

def backup_existing_compose_file():
    """Backup the existing docker-compose.yml file if it exists."""
    if os.path.exists("docker-compose.yml"):
        backup_file = "docker-compose.yml.bak"
        os.rename("docker-compose.yml", backup_file)
        logger.info(f"Existing docker-compose.yml backed up as {backup_file}")

def create_docker_network():
    """Create a custom Docker network for ThingsBoard."""
    network_name = "thingsboard_net"
    run_command(f"docker network create {network_name} || true", f"Creating Docker network '{network_name}'")
    return network_name

def get_user_config():
    """Prompt the user for custom configuration values."""
    http_port = input("[PROMPT] Enter HTTP port for ThingsBoard (default: 8080): ") or "8080"
    mqtt_port = input("[PROMPT] Enter MQTT port (default: 1883): ") or "1883"
    coap_port = input("[PROMPT] Enter CoAP port (default: 5683): ") or "5683"
    return http_port, mqtt_port, coap_port

def configure_environment():
    """Set environment-specific configurations."""
    env = input("[PROMPT] Choose environment [dev/prod] (default: dev): ").lower() or "dev"
    if env == "prod":
        logger.info("Production environment selected. Using optimized resource limits.")
        return {
            "JAVA_OPTS": "-Xms512m -Xmx1024m",
            "DB_POOL_SIZE": "50"
        }
    else:
        logger.info("Development environment selected. Using default settings.")
        return {
            "JAVA_OPTS": "-Xms256m -Xmx512m",
            "DB_POOL_SIZE": "20"
        }

def install_thingsboard_docker_compose(http_port, mqtt_port, coap_port):
    """Install ThingsBoard using Docker Compose with custom ports."""
    compose_file_content = f"""
version: '3.5'
services:
  tb:
    image: thingsboard/tb-postgres:latest
    container_name: tb
    ports:
      - "{http_port}:8080"
      - "{mqtt_port}:1883"
      - "{coap_port}:5683/udp"
    environment:
      TB_QUEUE_TYPE: kafka
      SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/thingsboard
      SPRING_DATASOURCE_USERNAME: tb_user
      SPRING_DATASOURCE_PASSWORD: tb_password
    depends_on:
      - postgres

  postgres:
    image: postgres:12
    container_name: postgres
    environment:
      POSTGRES_DB: thingsboard
      POSTGRES_USER: tb_user
      POSTGRES_PASSWORD: tb_password
    volumes:
      - ./data/db:/var/lib/postgresql/data
"""

    with open("docker-compose.yml", "w") as f:
        f.write(compose_file_content)

    run_command("docker-compose up -d", "Deploying ThingsBoard with Docker Compose")

def configure_firewall(http_port, mqtt_port, coap_port):
    """Configure firewall to allow ThingsBoard ports."""
    run_command(f"sudo ufw allow {http_port}", f"Allowing HTTP port {http_port}")
    run_command(f"sudo ufw allow {mqtt_port}", f"Allowing MQTT port {mqtt_port}")
    run_command(f"sudo ufw allow {coap_port}", f"Allowing CoAP port {coap_port}")
    run_command("sudo ufw enable", "Enabling the firewall")

def verify_installation():
    """Check the status of ThingsBoard Docker containers and print instructions."""
    run_command("docker-compose ps", "Checking running containers")
    logger.info("ThingsBoard should now be accessible via http://<your-ip>:8080")

def send_notification(email, success=True):
    """Send an email notification upon completion."""
    status = "SUCCESS" if success else "FAILURE"
    msg = MIMEText(f"The ThingsBoard installation completed with status: {status}")
    msg['Subject'] = "ThingsBoard Installation Status"
    msg['From'] = "noreply@example.com"
    msg['To'] = email

    try:
        with smtplib.SMTP("smtp.example.com", 587) as server:
            server.starttls()
            server.login("user", "password")
            server.sendmail(msg['From'], [msg['To']], msg.as_string())
        logger.info("[INFO] Notification email sent.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to send notification email: {e}")

def main_menu():
    """Display a menu for user to select operations."""
    while True:
        print("\n" + colored("=== ThingsBoard Installation Menu ===", "cyan", attrs=["bold"]))
        print(colored("1. Full Installation", "green"))
        print(colored("2. Verify Installation", "yellow"))
        print(colored("3. Configure Firewall", "yellow"))
        print(colored("4. Send Notification Email", "blue"))
        print(colored("5. Exit", "red"))

        choice = input(colored("Enter your choice [1-5]: ", "white", attrs=["bold"]))

        if choice == "1":
            full_installation()
        elif choice == "2":
            verify_installation()
        elif choice == "3":
            configure_firewall("8080", "1883", "5683")
        elif choice == "4":
            send_notification("admin@example.com")
        elif choice == "5":
            print(colored("Exiting. Goodbye!", "red"))
            break
        else:
            print(colored("[ERROR] Invalid choice, please try again.", "red"))

def full_installation():
    """Run the full installation process."""
    pre_install_check()
    update_and_upgrade_system()
    install_docker()
    backup_existing_compose_file()
    http_port, mqtt_port, coap_port = get_user_config()
    install_thingsboard_docker_compose(http_port, mqtt_port, coap_port)
    configure_firewall(http_port, mqtt_port, coap_port)
    verify_installation()
    send_notification("admin@example.com", success=True)

if __name__ == "__main__":
    main_menu()

