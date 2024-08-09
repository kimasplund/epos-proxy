const winston = require('winston');
const { format } = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');
const config = require('./config.json');

const logger = winston.createLogger({
  level: config.logLevel,
  format: format.combine(
    format.timestamp(),
    format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new DailyRotateFile({
      filename: `${config.logFile}-%DATE%`,
      datePattern: 'YYYY-MM-DD',
      maxSize: '20m',
      maxFiles: '14d'  // Keep logs for 14 days
    })
  ]
});

module.exports = logger;
