// Copyright 2025 SharpSir Group
// Licensed under the Apache License, Version 2.0
// See LICENSE file for details.
const path = require('path');

module.exports = {
  apps: [{
    name: 'reso-web-api',
    script: 'venv/bin/uvicorn',
    args: 'main:app --host 0.0.0.0 --port 3900',
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
