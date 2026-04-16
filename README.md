Volvo to MQTT Bridge (2025+ Google Models)
English 🇬🇧
This Python-based Docker container bridges the Volvo Connected Vehicle API with your local MQTT Broker. It is specifically tested and optimized for Volvo models (2025 and newer) using the Google built-in system (AAOS).
Features

    Battery & Charging: Real-time SoC (%), Electric Range, and Charging Status.
    Vehicle Status: Doors, Windows, Tyres (Tires), and Central Lock status.
    Engine & Fuel: Odometer, Fuel Level, and Engine status.
    Location: GPS Coordinates (Latitude/Longitude) and Heading.

📋 Prerequisites

    Volvo Developer Account:
        Go to Volvo Developer Portal. (https://developer.volvocars.com/)
        Create an account and a new App.
        Crucial: You must "Publish" the app and select all the APIs Scope in your App dashboard:
            Connected Vehicle API
            Energy API
            Location API (v1)
🔑 Volvo Developer Portal: App Settings

When creating your application on the Volvo Developer Portal, use these specific settings:
Field	Value / Recommendation
Application Name	Volvo MQTT Bridge (or any name you like)
Redirect URIs	http://localhost:8080/callback (Required for the login process)
Purpose	Personal Home Automation
Terms of Services URL	http://localhost:8080/terms (Can be a dummy URL for personal use)

        Copy your Client ID and Client Secret.
    VCC API Key: In your Volvo dashboard, copie the VCC API Key (Primary).
    MQTT Broker: You need an IP address, port, and (optional) credentials for your broker (e.g., Mosquitto).

🚀 Quick Start

    Preparation:
        Download the project files to a folder on your server.
        Rename config.example.json to config.json and fill in your credentials:
        json

        {
          "client_id": "YOUR_VOLVO_ID",
          "client_secret": "YOUR_VOLVO_SECRET",
          "vcc_api_key": "YOUR_VCC_KEY",
          "vin": "YV1XXXXXXXXXXXXXX",
          "mqtt_broker": "192.168.x.x"
        }

        Utilisez le code avec précaution.
    Deployment with Docker:
        Open a terminal in the project folder.
        Build the image: docker build -t volvo-mqtt-bridge .
        Launch:
        bash

        docker run -d \
          --name volvo-bridge \
          -v $(pwd)/tokens.json:/app/tokens.json \
          --restart unless-stopped \
          volvo-mqtt-bridge

        Utilisez le code avec précaution.
    First Run: Check the logs (docker logs -f volvo-bridge). The script will provide a URL to log in to your Volvo account for the initial authorization.

Français 🇫🇷
Ce conteneur Docker basé sur Python fait le pont entre l'API Volvo Connected Vehicle et votre broker MQTT local. Il est spécifiquement testé et optimisé pour les modèles Volvo (2025 et plus récents) équipés du système Google intégré (AAOS).
Fonctionnalités

    Batterie & Charge : Niveau de charge (SoC %) en temps réel, autonomie électrique et statut de charge.
    État du Véhicule : État des portes, des fenêtres, des pneus et du verrouillage centralisé.
    Moteur & Carburant : Odomètre (kilométrage), niveau d'essence et état du moteur.
    Localisation : Coordonnées GPS (Latitude/Longitude) et orientation (Heading).

📋 Prérequis

    Compte Développeur Volvo :
        Rendez-vous sur le Portail Développeur Volvo.
        Créez un compte et une nouvelle App.
        Crucial : Vous devez "Publier" (Publish) l'application et sélectionner tous les APIs Scopes dans votre tableau de bord :
            Connected Vehicle API
            Energy API
            Location API (v1)

🔑 Réglages de l'application (App Settings)
Lors de la création de votre application, utilisez ces paramètres spécifiques :
Champ	Valeur / Recommandation
Application Name	Volvo MQTT Bridge (ou le nom de votre choix)
Redirect URIs	http://localhost:8080/callback (Indispensable pour l'authentification)
Purpose	Personal Home Automation
Terms of Services URL	http://localhost:8080/terms (Peut être une URL fictive)

    Copiez votre Client ID et votre Client Secret.
    VCC API Key : Dans votre tableau de bord Volvo, copiez la VCC API Key (Primary).
    Broker MQTT : Vous aurez besoin de l'adresse IP, du port et des identifiants (optionnels) de votre broker (ex: Mosquitto).

🚀 Installation Rapide

    Préparation :
        Téléchargez les fichiers du projet dans un dossier sur votre serveur.
        Renommez config.example.json en config.json et remplissez vos identifiants :
        json

        {
          "client_id": "VOTRE_ID_VOLVO",
          "client_secret": "VOTRE_SECRET_VOLVO",
          "vcc_api_key": "VOTRE_CLE_VCC",
          "vin": "YV1XXXXXXXXXXXXXX",
          "mqtt_broker": "192.168.x.x"
        }

        Utilisez le code avec précaution.
    Déploiement avec Docker :
        Ouvrez un terminal dans le dossier du projet.
        Construire l'image : docker build -t volvo-mqtt-bridge .
        Lancer le conteneur :
        bash

        docker run -d \
          --name volvo-bridge \
          -v $(pwd)/tokens.json:/app/tokens.json \
          --restart unless-stopped \
          volvo-mqtt-bridge

        Utilisez le code avec précaution.
    Premier lancement : Vérifiez les logs (docker logs -f volvo-bridge). Le script affichera une URL pour vous connecter à votre compte Volvo afin de valider l'autorisation initiale.