const fs = require('fs');
const config = require('./config.json');

function validateConfig() {
  if (!config.logLevel) {
    throw new Error('logLevel is not defined in config.json');
  }
  if (!config.logFile) {
    throw new Error('logFile is not defined in config.json');
  }
  if (!config.hostMap || typeof config.hostMap !== 'object') {
    throw new Error('hostMap is not properly defined in config.json');
  }
  if (!config.savePath) {
    throw new Error('savePath is not defined in config.json');
  }
  if (!fs.existsSync('cert/server.key') || !fs.existsSync('cert/server.cert')) {
    throw new Error('SSL certificates are not properly configured');
  }
}

module.exports = { validateConfig };
