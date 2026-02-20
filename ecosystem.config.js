// Copyright 2025 SharpSir Group
// Licensed under the Apache License, Version 2.0
// See LICENSE file for details.
const path = require('path');
const fs = require('fs');

// Load .env file
const envPath = path.join(__dirname, '.env');
const envConfig = {};
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  envContent.split('\n').forEach(line => {
    const match = line.match(/^([^#=]+)=(.*)$/);
    if (match) {
      let val = match[2].split('#')[0].trim();
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      envConfig[match[1].trim()] = val;
    }
  });
}

// API configuration from .env with defaults
const API_HOST = envConfig.RESO_API_HOST || '0.0.0.0';
const API_PORT = envConfig.RESO_API_PORT || '3900';
const SSL_CERT = (envConfig.RESO_SSL_CERTFILE || '').trim();
const SSL_KEY = (envConfig.RESO_SSL_KEYFILE || '').trim();
const certExists = SSL_CERT && fs.existsSync(SSL_CERT);
const keyExists = SSL_KEY && fs.existsSync(SSL_KEY);
const hasSsl = SSL_CERT && SSL_KEY && certExists && keyExists;
const sslArgs = hasSsl ? ` --ssl-certfile ${SSL_CERT} --ssl-keyfile ${SSL_KEY}` : '';

if (SSL_CERT || SSL_KEY) {
  console.log('[ecosystem] RESO_SSL_CERTFILE:', SSL_CERT, certExists ? 'OK' : 'NOT FOUND');
  console.log('[ecosystem] RESO_SSL_KEYFILE:', SSL_KEY, keyExists ? 'OK' : 'NOT FOUND');
  if (!hasSsl) console.log('[ecosystem] Running without SSL - fix paths in .env');
}

module.exports = {
  apps: [{
    name: 'reso-web-api',
    script: 'venv/bin/uvicorn',
    args: `main:app --host ${API_HOST} --port ${API_PORT}${sslArgs}`,
    cwd: path.join(__dirname, 'api'),
    interpreter: 'none',
    env: {
      // Environment variables are loaded from ../.env by the app
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    error_file: path.join(__dirname, 'api/logs/error.log'),
    out_file: path.join(__dirname, 'api/logs/out.log'),
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
  }]
};
