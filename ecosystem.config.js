module.exports = {
  apps: [
    { 
      name: "VIP-Max", script: "botpremium.py", interpreter: "python3",
      env: { 
        BOT_NAME: "peaxel20", 
        API_KEY: process.env.API_20, 
        PRIVATE_KEY: process.env.PRIV_20 
      }
    },
    { 
      name: "VIP-Lite", script: "botpremium.py", interpreter: "python3",
      env: { 
        BOT_NAME: "peaxel21", 
        API_KEY: process.env.API_21, 
        PRIVATE_KEY: process.env.PRIV_21 
      }
    }
  ]
};
