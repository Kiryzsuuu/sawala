module.exports = {
  apps: [
    {
      name: "sawala",
      cwd: "/home/Inspira/sawala",
      interpreter: "/home/Inspira/sawala/venv/bin/python",
      script: "run.py",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
    },
  ],
};
