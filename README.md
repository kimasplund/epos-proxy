
# ePOS Proxy Server

A lightweight proxy server designed to bridge the gap between modern HTTPS-based ePOS systems and older HTTP-only printers, such as the Epson TM-70II with a UB-R04 network card. This tool facilitates the seamless transfer of XML printing data from platforms like Odoo POS to legacy printers.

## Table of Contents
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Example](#example)
- [Contributing](#contributing)
- [License](#license)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/epos-proxy.git
   ```
2. Navigate to the project directory:
   ```bash
   cd epos-proxy
   ```
3. Install the required dependencies:
   ```bash
   npm install
   ```
4. Configure printers in config.json (#configuration)
   ```
5. (Optional) Run the provided script to set up the environment:
   ```bash
   chmod +x run-1st.sh
   ./run-1st.sh
   ```

## Configuration

Configure the server by editing the `config.json` file. The `hostMap` section allows you to map printer names to their respective HTTP addresses.

Example `config.json`:
```json
{
  "hostMap": {
    "epos-printer1.local": "http://192.168.14.217",
    "epos-printer2.local": "http://192.168.14.101"
  }
}
```

Ensure that your internal DNS points to the IP address of the machine running this proxy server.

## Usage

Start the proxy server using Node.js:
```bash
node proxyServer.js
```

For production environments, it's recommended to use `pm2` to keep the server running:
```bash
pm2 start proxyServer.js
```

## Example

When you send a print job to `https://epos-printer1.local`, the proxy server will forward the request to `http://192.168.14.217`, enabling the older printer to process the job over HTTP.

## Contributing

Contributions are welcome! If you have suggestions for improvements, feel free to fork the repository and submit a pull request. You can also open an issue for any bugs or feature requests.

To contribute:
1. Fork the repository.
2. Create a new branch for your feature or fix.
3. Make your changes.
4. Submit a pull request.

Please ensure that your changes are well-tested and documented.

## License

This project is licensed under the MIT License. You are free to use, modify, and distribute this software as long as the original license and copyright notice are included. See the [LICENSE](LICENSE) file for details.
