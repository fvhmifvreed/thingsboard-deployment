#!/bin/bash
# Auth: Fahmi Fareed

# ThingsBoard CE Automated Installation Script for Ubuntu with Error Handling

LOG_FILE="/var/log/thingsboard_install.log"

log_and_exit() {
  echo "Error: $1" | tee -a $LOG_FILE
  exit 1
}

log_info() {
  echo "Info: $1" | tee -a $LOG_FILE
}

log_info "Starting ThingsBoard installation process..."

# Step 1: Update the system and install Java 17 (OpenJDK)
log_info "Step 1: Installing Java 17..."
sudo apt update || log_and_exit "Failed to update package lists"
sudo apt install -y openjdk-17-jdk || log_and_exit "Failed to install OpenJDK 17"
sudo update-alternatives --config java || log_and_exit "Failed to configure Java alternatives"

log_info "Verifying Java installation..."
java -version || log_and_exit "Java installation verification failed"

# Step 2: Download and install ThingsBoard service
log_info "Step 2: Installing ThingsBoard service..."
wget https://github.com/thingsboard/thingsboard/releases/download/v3.8.1/thingsboard-3.8.1.deb || log_and_exit "Failed to download ThingsBoard package"
sudo dpkg -i thingsboard-3.8.1.deb || log_and_exit "Failed to install ThingsBoard package"

# Step 3: Install and configure PostgreSQL
log_info "Step 3: Installing and configuring PostgreSQL..."
sudo apt install -y postgresql-common || log_and_exit "Failed to install postgresql-common"
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh || log_and_exit "Failed to configure PostgreSQL repository"
sudo apt update || log_and_exit "Failed to update package lists for PostgreSQL"
sudo apt install -y postgresql-16 || log_and_exit "Failed to install PostgreSQL 16"
sudo service postgresql start || log_and_exit "Failed to start PostgreSQL service"

# Set password for PostgreSQL user and create ThingsBoard database
log_info "Configuring PostgreSQL..."
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_secure_password';" || log_and_exit "Failed to set PostgreSQL user password"
sudo -u postgres psql -c "CREATE DATABASE thingsboard;" || log_and_exit "Failed to create ThingsBoard database"

# Step 4: Configure ThingsBoard
log_info "Configuring ThingsBoard..."
sudo bash -c 'cat > /etc/thingsboard/conf/thingsboard.conf <<EOL
export DATABASE_TS_TYPE=sql
export SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/thingsboard
export SPRING_DATASOURCE_USERNAME=postgres
export SPRING_DATASOURCE_PASSWORD=your_secure_password
export SQL_POSTGRES_TS_KV_PARTITIONING=MONTHS
EOL' || log_and_exit "Failed to configure ThingsBoard"

# Step 5: Optional memory update for slow machines
log_info "Updating ThingsBoard memory configuration for slow machines..."
sudo bash -c 'echo "export JAVA_OPTS=\\"$JAVA_OPTS -Xms2G -Xmx2G\\"" >> /etc/thingsboard/conf/thingsboard.conf' || log_and_exit "Failed to update memory configuration"

# Step 6: Run installation script
log_info "Running ThingsBoard installation script..."
sudo /usr/share/thingsboard/bin/install/install.sh --loadDemo || log_and_exit "Failed to run ThingsBoard installation script"

# Step 7: Start ThingsBoard service
log_info "Starting ThingsBoard service..."
sudo service thingsboard start || log_and_exit "Failed to start ThingsBoard service"

log_info "Installation complete. Access ThingsBoard at http://<your_server_IP>:8080"
