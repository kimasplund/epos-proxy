#!/bin/bash

# Prompt the user to confirm if they have configured printers in config.json
read -p "Have you configured the printers in config.json? (Y/N): " user_input

# Convert the input to uppercase to handle lower case responses
user_input=$(echo "$user_input" | tr '[:lower:]' '[:upper:]')

# Check the user's input
if [ "$user_input" == "Y" ]; then
    echo "Continuing with the setup..."
elif [ "$user_input" == "N" ]; then
    echo "Please configure the printers in config.json before running this script."
    exit 1
else
    echo "Invalid input. Please enter Y or N."
    exit 1
fi

# Navigate to the script's directory
cd "$(dirname "$0")"

# Ensure the cert directory exists
mkdir -p cert

# Check and generate SSL certificates
cert_file="./cert/server.cert"
if [ ! -f "$cert_file" ]; then
  echo "SSL certificate not found. Generating a new one..."
  openssl req -nodes -new -x509 -keyout cert/server.key -out cert/server.cert -days 3650
else
  expiration_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d '=' -f 2)
  expiration_secs=$(date -d "$expiration_date" +%s)
  current_secs=$(date +%s)
  days_left=$(( (expiration_secs - current_secs) / 86400 ))

  if [ "$days_left" -le 60 ]; then
    echo "SSL certificate is expiring in less than 60 days. Generating a new one..."
    openssl req -nodes -new -x509 -keyout cert/server.key -out cert/server.cert -days 3650
  fi
fi

# Install or update npm modules
echo "Installing or updating npm modules..."
npm install

# Start the server using npm start
echo "Starting the server..."
npm start