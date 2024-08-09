
const express = require('express');
const https = require('https');
const { createProxyMiddleware } = require('http-proxy-middleware');
const fs = require('fs');
const config = require('./config.json');
const logger = require('./logger');
const { savePrintData, deleteOldPrintFiles } = require('./fileOperations');
const { validateConfig } = require('./configValidation');

validateConfig();

const app = express();

const proxyMiddlewares = {};
for (const [hostname, target] of Object.entries(config.hostMap)) {
  proxyMiddlewares[hostname] = createProxyMiddleware({
    target: target,
    changeOrigin: true,
    selfHandleResponse: false,
    onProxyReq: async (proxyReq, req) => {
      let body = [];
      req.on('data', chunk => {
        body.push(chunk);
      }).on('end', async () => {
        try {
          body = Buffer.concat(body).toString();

          // Directly save the received payload as an XML file
          const datePart = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
          await savePrintData(body, target, datePart);

        } catch (error) {
          logger.error('Error processing request body:', error);
        }
      });
    }
  });

  app.use(`/${hostname}`, proxyMiddlewares[hostname]);
}

// Run cleanup of old print files once a day
setInterval(deleteOldPrintFiles, 24 * 60 * 60 * 1000);  // 24 hours in milliseconds

// Other configurations and app.listen() as needed
