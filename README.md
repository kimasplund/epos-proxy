# ePOS Proxy Server

A proxy server that allows communication with ePOS printers that don't support HTTPS. This server acts as a middleman, accepting HTTPS requests and forwarding them to printers via HTTP or HTTPS, while providing DNS resolution, logging, and a web interface.

## Features

- HTTPS to HTTP/HTTPS proxy for ePOS printers
- Support for both HTTP-only printers and HTTPS-capable printers
- Self-signed certificate generation
- Built-in DNS server for printer name resolution
- Simplified printer configuration
- Automatic configuration reloading (no restart needed)
- Request logging
- Print data storage for debugging
- Web interface for administration and monitoring
- Email receipt functionality with customizable templates
- Docker support with automatic updates

## Installation

### Using Docker (Recommended)

1. Clone this repository:
   ```
   git clone https://github.com/kimasplund/epos-proxy.git
   cd epos-proxy
   ```

2. Configure your printers in `printers.config` (see Configuration section below)

3. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file to set your admin password, email settings, and other configuration options.

4. Start the container:
   ```
   docker-compose up -d
   ```

The server should now be running on HTTPS port 443, with a DNS server on port 53, and the web interface accessible at https://proxy.epos/ if you configure your client to use the server as a DNS server.

### Manual Installation

1. Clone this repository:
   ```
   git clone https://github.com/kimasplund/epos-proxy.git
   cd epos-proxy
   ```

2. Install required packages:
   ```
   pip install -r app/requirements.txt
   ```

3. Configure your printers in `printers.config` (see Configuration section below)

4. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file to set your admin password, email settings, and other configuration options.

5. Generate a self-signed certificate:
   ```
   mkdir -p app/cert
   openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
     -keyout app/cert/server.key -out app/cert/server.cert \
     -subj "/C=SE/ST=Stockholm/L=Stockholm/O=ePOS Proxy/CN=epos-proxy"
   ```

6. Start the server:
   ```
   cd app
   python main.py
   ```

The server should now be running on HTTPS port 443, with a DNS server on port 53, and the web interface accessible at https://proxy.epos/ if you configure your client to use the server as a DNS server.

## Configuration

### Simplified Printer Configuration

The easiest way to configure printers is by editing the `printers.config` file:

```
# HTTP Printers (default if protocol not specified)
kitchen = 192.168.1.100
bar = 192.168.1.101

# HTTPS Printers (explicitly specify https://)
reception = https://192.168.1.102
office = https://192.168.1.103
```

Each line follows the format `printer_name = ip_address_or_url`, where:
- `printer_name` is how you'll refer to the printer in your ePOS requests (do not include .epos suffix)
- `ip_address_or_url` is the printer's IP address or full URL:
  - For HTTP printers: simply use the IP address (e.g., `192.168.1.100`)
  - For HTTPS printers: use the full URL (e.g., `https://192.168.1.102`)
  - For custom ports: add the port (e.g., `192.168.1.100:8080` or `https://192.168.1.102:8443`)

The DNS server will automatically make these printers available as `kitchen.epos`, `bar.epos`, `reception.epos`, and `office.epos`.

### Printer Protocol Support

The ePOS Proxy Server supports both HTTP-only printers and HTTPS-capable printers:

1. **HTTP Printers**: These printers only accept HTTP connections. The proxy server will:
   - Accept HTTPS requests from clients
   - Convert them to HTTP requests and forward to the printer
   - Return the printer's response via HTTPS to the client

2. **HTTPS Printers**: These printers already support HTTPS connections. Using the proxy still provides benefits:
   - Unified DNS management for all printers
   - Centralized logging and monitoring
   - Email receipt functionality
   - Print job history through the web interface

### Dynamic Configuration

The server now watches for changes to the `printers.config` file and automatically reloads the configuration when changes are detected. This means you can add, remove, or update printers without having to restart the server.

When you edit and save the `printers.config` file, the server will:
1. Detect the changes automatically
2. Reload the printer configuration
3. Update the DNS records if the DNS server is enabled
4. Make the new configuration immediately available for use

You can check the status of the configuration watcher via the `/config` endpoint.

For Docker installations, you still need to edit the `printers.config` file that is mounted into the container, but you no longer need to restart the container for changes to take effect.

If you want to disable this feature, you can use the `--no-watch-config` command-line option.

### Advanced Configuration

For advanced configuration, you can edit the `config.json` file:

```json
{
  "logLevel": "INFO",
  "logDirectory": "logs",
  "logMax_size": 10,
  "logBackup_count": 5,
  "dataDirectory": "data",
  "retentionDays": 7,
  "hostMap": {
    "kitchen": "http://192.168.1.100",
    "bar": "http://192.168.1.101",
    "reception": "https://192.168.1.102",
    "office": "https://192.168.1.103"
  },
  "enableDns": true,
  "dnsPort": 53
}
```

Note: Printer configurations in `printers.config` will override those in `config.json`.

### Email Configuration

To use the email functionality, you need to configure your SMTP server settings in the `.env` file:

```
# Email configuration (SMTP server settings)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=username
SMTP_PASSWORD=password
SMTP_USE_TLS=True
SMTP_USE_SSL=False

# Email sender information
EMAIL_FROM=receipts@yourdomain.com
EMAIL_FROM_NAME=Your Business Name
```

## Built-in DNS Server

The ePOS Proxy Server includes a built-in DNS server that allows you to resolve printer hostnames to their IP addresses without modifying the hosts file on your client devices.

### How It Works

The DNS server listens on port 53 (UDP) by default and resolves the following hostnames:

1. **proxy.epos** - Resolves to the ePOS Proxy Server's IP address, allowing you to access the web interface at https://proxy.epos/
2. **printer_name.epos** - Resolves to the printer's IP address for any printer configured in `printers.config` or `config.json`

When you configure a printer named "kitchen" in your configuration, the DNS server will automatically make it available as "kitchen.epos". You can then send requests to this hostname from your client applications.

### Client Configuration

To use the DNS server, configure your client devices to use the ePOS Proxy Server as their DNS server:

1. Set the DNS server on your client device to the IP address of the ePOS Proxy Server
2. In your application, use the following hostnames:
   - **proxy.epos** - To access the ePOS Proxy Server web interface
   - **printer_name.epos** - To send ePOS requests to printers

For example, if your ePOS Proxy Server is running at 192.168.1.10, and you have a printer configured as "kitchen", you can:

1. Configure your client device to use 192.168.1.10 as its DNS server
2. In your browser, access https://proxy.epos/ to use the web interface
3. In your application, send ePOS requests to https://kitchen.epos/

### Configuration Options

You can configure the DNS server in the `config.json` file:

```json
{
  "enableDns": true,
  "dnsPort": 53
}
```

- `enableDns`: Set to `true` to enable the DNS server, or `false` to disable it
- `dnsPort`: The UDP port for the DNS server (default: 53)

You can also use command line options when running the server:

```
python main.py --no-dns           # Disable the DNS server
python main.py --dns-port=5353    # Use a different port (useful if port 53 is already in use)
```

## Web Interface

The ePOS Proxy Server includes a web interface for administration, monitoring, and sending email receipts. The web interface is accessible at https://proxy.epos/ when using the built-in DNS server, or directly at https://your-server-address/, and requires authentication with the admin credentials set in the `.env` file.

### Features

- **Dashboard**: Overview of system status and recent activity
- **Print Jobs**: View and manage print jobs, send email receipts
- **Email Templates**: Create and customize email receipt templates
- **Settings**:
  - **Users**: Manage user accounts
  - **Email Themes**: Customize the appearance of email receipts
  - **Company Branding**: Configure company information and logo for email receipts

### Email Receipt Functionality

The ePOS Proxy Server can send email receipts based on print jobs. The email receipts are fully customizable through the web interface. You can:

- Create and edit email templates with custom HTML and CSS
- Define email themes with different colors and fonts
- Configure company branding with logo and contact information
- Preview email templates before sending
- Send email receipts to customers for any print job

### Initial Setup

When you first start the server with the web interface enabled, it will:

1. Initialize the database
2. Create the admin user from the `.env` file settings
3. Create default email templates, themes, and company branding
4. Generate the required directories and assets

You can then access the web interface at https://proxy.epos/ (if using the built-in DNS) or https://your-server-address/ and log in with the admin credentials.

### Security

Access to the web interface is protected by authentication. By default, only an admin user is created. You can create additional users with different permission levels through the web interface.

## Usage

Once the server is running, you can send HTTPS requests to it, which will be forwarded to the configured printers via HTTP or HTTPS.

For example, if your server is running and you have a printer configured as "kitchen", you can send a request to:

```
https://kitchen.epos/cgi-bin/epos/service.cgi
```

The server will forward this request to:
- `http://[kitchen-ip]/cgi-bin/epos/service.cgi` (if configured as HTTP)
- `https://[kitchen-ip]/cgi-bin/epos/service.cgi` (if configured as HTTPS)

## API Endpoints

### Proxy API
- `/health`: Health check endpoint
- `/printers`: List configured printers
- `/dns`: DNS server status
- `/config`: Configuration watcher status
- `/files`: List saved print files

### Web API
- `/api/token`: Authentication endpoint
- `/api/users`: User management
- `/api/email/templates`: Email template management
- `/api/email/themes`: Email theme management
- `/api/branding`: Company branding management
- `/api/email/send`: Send email receipts
- `/api/print_jobs`: Print job management

## Command Line Options

```
python main.py --help                    # Show help
python main.py --config=config.json      # Specify config file
python main.py --host=127.0.0.1          # Specify host
python main.py --port=8443               # Specify port
python main.py --no-dns                  # Disable DNS server
python main.py --dns-port=5353           # Specify DNS port
python main.py --no-watch-config         # Disable config watching
python main.py --no-web                  # Disable web interface
python main.py --web-secret-key=secret   # Specify web session secret key
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Kim Asplund - [kim.asplund@gmail.com](mailto:kim.asplund@gmail.com) - [https://asplund.kim](https://asplund.kim)
