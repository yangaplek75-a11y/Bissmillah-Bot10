module.exports = {
  apps: [
    { 
      name: "VIP-Max", script: "botpremium.py", interpreter: "python3",
      env: { 
        BOT_NAME: "Peaxel20", 
        API_KEY: process.env.API_20, 
        PRIVATE_KEY: process.env.PRIV_20 
      }
    },
    { 
      name: "VIP-Lite", script: "botpremium.py", interpreter: "python3",
      env: { 
        BOT_NAME: "Peaxel21", 
        API_KEY: process.env.API_21, 
        PRIVATE_KEY: process.env.PRIV_21 
      }
    },
    { 
      name: "VIP-Turbo", script: "botpremium.py", interpreter: "python3",
      env: { 
        BOT_NAME: "Peaxel22", 
        API_KEY: process.env.API_22, 
        PRIVATE_KEY: process.env.PRIV_22 
      }
    },
    { 
      name: "VIP-Dex", script: "botpremium.py", interpreter: "python3",
      env: { 
        BOT_NAME: "Peaxel23", 
        API_KEY: process.env.API_23, 
        PRIVATE_KEY: process.env.PRIV_23 
      }
    },
    { 
      name: "VIP-Solar", script: "botpremium.py", interpreter: "python3",
      env: { 
        BOT_NAME: "Peaxel24", 
        API_KEY: process.env.API_24, 
        PRIVATE_KEY: process.env.PRIV_24 
      }
    }
  ]
};