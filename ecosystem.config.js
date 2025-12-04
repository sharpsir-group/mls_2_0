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
      envConfig[match[1].trim()] = match[2].trim();
    }
  });
}

// API configuration from .env with defaults
const API_HOST = envConfig.RESO_API_HOST || '0.0.0.0';
const API_PORT = envConfig.RESO_API_PORT || '3900';

module.exports = {
  apps: [{
    name: 'reso-web-api',
    script: 'venv/bin/uvicorn',
    args: `main:app --host ${API_HOST} --port ${API_PORT}`,
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
