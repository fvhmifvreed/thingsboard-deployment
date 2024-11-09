import argparse
import threading
import requests
import json
import paramiko
import os

# Parse command-line arguments
parser = argparse.ArgumentParser(description='This script aims to automate the installation and configuration of the Thingsboard IoT Gateway platform on multiple devices at once.')
parser.add_argument('action', choices=['deploy', 'update'], help='Choose whether to deploy or update Thingsboard IoT')
args = parser.parse_args()

# Importing models and REST client class from Community Edition version
from tb_rest_client.rest_client_ce import *
from tb_rest_client.rest import ApiException

# Global variables
gt_user = 'root'
gt_password = '12345678'
tb_url = 'http://192.168.110.20:8080'
remote_config_directory = '/etc/thingsboard-gateway/config/'

if args.action == "deploy":
    # Deploy commands
    cmd = [
        f'echo {gt_password} | sudo -S apt update -y && sudo apt upgrade -y',
        f'echo {gt_password} | sudo -S apt install python3 python3-dev',
        f'echo {gt_password} | sudo -S wget https://github.com/thingsboard/thingsboard-gateway/releases/latest/download/python3-thingsboard-gateway.deb',
        f'echo {gt_password} | sudo -S apt install ./python3-thingsboard-gateway.deb -y',
    ]
else:
    # Update commands
    cmd = [
        f'echo {gt_password} | sudo -S sed -i \'s/"clientId":.*,/"clientId": "\'$(hostname -s)\'",/\' /etc/thingsboard-gateway/config/mqtt.json'
        f'echo {gt_password} | sudo -S systemctl restart thingsboard-gateway'
    ]

jwt_token = "Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJhbGV4YW5kcmUudGhlaXNAZmluZG1vcmUucHQiLCJ1c2VySWQiOiJhODM2NWM2MC1kYWE0LTExZWQtOGM4MS0yOTI1YTFiOWZjOTAiLCJzY29wZXMiOlsiVEVOQU5UX0FETUlOIl0sInNlc3Npb25JZCI6ImFjNDAxZGFlLWNhYzgtNGI3Zi04ZTdlLTBkNmM3MGZiMDJkNSIsImlzcyI6InRoaW5nc2JvYXJkLmlvIiwiaWF0IjoxNjgzODA1ODUyLCJleHAiOjE2ODM4MTQ4NTIsImZpcnN0TmFtZSI6IkFsZXhhbmRyZSIsImxhc3ROYW1lIjoiVGhlaXMiLCJlbmFibGVkIjp0cnVlLCJpc1B1YmxpYyI6ZmFsc2UsInRlbmFudElkIjoiMzAxMzE1NjAtZGE5Ni0xMWVkLTlhYjYtNzU2NTI1NGI1Yzc3IiwiY3VzdG9tZXJJZCI6IjEzODE0MDAwLTFkZDItMTFiMi04MDgwLTgwODA4MDgwODA4MCJ9.ZdtB266BZFtzIYWAXpimq-vPNwuT5e3smg34WKbwDK39GR_Rq9DA-vEQTXppISkh3XfpO6NaHImAclZFUljIJw"

headers = {"Content-Type": "application/json", "X-Authorization": jwt_token}

max_threads = 10
semaphore = threading.BoundedSemaphore(value=max_threads)

def execute_ssh_command(client, command):
    """
    Executes an SSH command and returns the output.
    """
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.readlines()
    return output

def deploy_gateway_and_configure_device(gt_address):
    """
    Deploys ThingsBoard gateway and configures the device.
    """
    try:
        # Connecting to the IoT device via SSH
        with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=gt_address, username=gt_user, password=gt_password, timeout=5)

            # Retrieve the name of the IoT device
            stdin, stdout, stderr = client.exec_command('hostname -s')
            gt_name = stdout.read().decode().strip()

            if args.action == "deploy":
                # Create a ThingsBoard device with the IoT device name
                requests.post(f"{tb_url}/api/device", headers=headers, data=json.dumps({"name": gt_name, "type": "device"})).json()
                
            else:
                # Retrieve device ID by name
                device_info = requests.get(f"{tb_url}/api/tenant/devices?deviceName={gt_name}", headers=headers).json()

                # Retrieve the device ID from the parsed JSON response 
                if "id" in device_info:
                    device_id = device_info["id"]["id"]
                else:
                    raise ValueError(device_info.get("message", "Network error!"))

                # Get the access token of the ThingsBoard device
                response = requests.get(f"{tb_url}/api/device/{device_id}/credentials", headers=headers)
                access_token = response.json().get("credentialsId")

                # Replace the access token in the configuration file
                cmd.insert(-1, f'echo {gt_password} | sudo -S sed -i "s/accessToken:.*/accessToken: {access_token}/g" /etc/thingsboard-gateway/config/tb_gateway.yaml')

                # Traverse through the files in the local directory using os.walk()
                for root, dirs, files in os.walk("gateway_conf"):
                    for filename in files:
                        # Copy the file to the remote host
                        sftp = client.open_sftp()
                        sftp.put(os.path.join(root, filename), os.path.join(remote_config_directory, filename))
                        sftp.close()

            # Execute all commands defined in "cmd" array
            success = True
            for command in cmd:
                stdin, stdout, stderr = client.exec_command(command, get_pty=True)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    print(f"Command failed for device {gt_address}: {command}")
                    success = False
                    break

            if success:
                print(f"All commands executed successfully for device {gt_address}")

    except paramiko.AuthenticationException:
        print(f"Authentication failed for {gt_address}")
    except paramiko.SSHException as ssh_ex:
        print(f"SSH error occurred for {gt_address}: {str(ssh_ex)}")
    except Exception as ex:
        print(f"An error occurred for {gt_address}: {str(ex)}")
    finally:
        semaphore.release()

# Read the gateway addresses from a file
with open('gateways.txt', 'r') as f:
    gateways = [line.strip() for line in f]

threads = []
for gt_address in gateways:
    semaphore.acquire()

    # Create a thread for each device 
    thread = threading.Thread(target=deploy_gateway_and_configure_device, args=[gt_address])
    thread.start()
    threads.append(thread)

# Wait for all threads to complete
for thread in threads:
    thread.join()
