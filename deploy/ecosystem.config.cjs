// PM2 ecosystem config for AmarktAI Marketing
// Usage:
//   pm2 start deploy/ecosystem.config.cjs
//   pm2 save
//   pm2 startup  (then run the printed command as root)

module.exports = {
  apps: [
    // ── FastAPI backend ────────────────────────────────────────────────────
    {
      name: "amarktai-marketing-api",
      cwd: "/var/www/amarktai-marketing/repo/backend",
      script: ".venv/bin/uvicorn",
      args: "app.main:app --host 127.0.0.1 --port 8010 --workers 2",
      interpreter: "none",
      env: {
        NODE_ENV: "production",
      },
      // Load backend/.env automatically via pydantic-settings
      error_file: "/var/log/pm2/amarktai-marketing-api-error.log",
      out_file: "/var/log/pm2/amarktai-marketing-api-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      restart_delay: 3000,
      max_restarts: 10,
      watch: false,
      autorestart: true,
    },

    // ── Celery worker ──────────────────────────────────────────────────────
    {
      name: "amarktai-marketing-worker",
      cwd: "/var/www/amarktai-marketing/repo/backend",
      script: ".venv/bin/celery",
      args: "-A app.workers.celery_app worker --loglevel=info --concurrency=2",
      interpreter: "none",
      error_file: "/var/log/pm2/amarktai-marketing-worker-error.log",
      out_file: "/var/log/pm2/amarktai-marketing-worker-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      restart_delay: 5000,
      max_restarts: 5,
      watch: false,
      autorestart: true,
    },

    // ── Celery Beat (scheduler) ────────────────────────────────────────────
    {
      name: "amarktai-marketing-beat",
      cwd: "/var/www/amarktai-marketing/repo/backend",
      script: ".venv/bin/celery",
      args: "-A app.workers.celery_app beat --loglevel=info",
      interpreter: "none",
      error_file: "/var/log/pm2/amarktai-marketing-beat-error.log",
      out_file: "/var/log/pm2/amarktai-marketing-beat-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      restart_delay: 5000,
      max_restarts: 5,
      watch: false,
      autorestart: true,
    },
  ],
};
