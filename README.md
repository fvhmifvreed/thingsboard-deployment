# Thingsboard IoT Deployment Script

This project aims to automate the installation and configuration of the Thingsboard IoT Gateway platform on multiple devices at once.

## Usage

1. Clone the repository to your local machine.
2. Install the required packages by running `pip install -r requirements.txt`.
3. Add the IP addresses of the devices to the `gateways.txt` file, with each IP address on a new line.
4. Review the installation commands in the `cmd` array of `main.py` and modify them with caution, as any incorrect changes may disrupt the script's functionality.
   - Exercise caution while modifying the commands as they are crucial for the deployment process. Incorrect changes can lead to unexpected behavior or errors.
5. If necessary, modify any additional configuration files for the Thingsboard IoT Gateway located in the `gateway_conf/` directory.
   - Exercise caution when modifying any configuration files in the gateway_conf/ directory, as the Python code relies on these files for proper functionality. Any removal or incorrect modification of these files may result in the script not functioning as intended.
6. Execute the deployment script by running the command `python main.py deploy` or `python main.py update`, depending on your desired action.
   - Use `python main.py deploy` to deploy the Thingsboard IoT Gateway, executing the commands specified in the `cmd` array.
   - Use `python main.py update` to update the Thingsboard IoT Gateway configuration on the devices, executing the update commands specified in the `cmd` array.
