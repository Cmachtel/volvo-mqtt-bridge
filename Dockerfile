# Utilise l'image Python 3.11 légère
FROM python:3.11-slim

# Définit le répertoire de travail dans le conteneur
WORKDIR /app

# Fuseau horaire ---
# Installe tzdata pour permettre le réglage de l'heure locale
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Logs en temps réel ---
# Force Python à afficher les logs immédiatement sans les garder en mémoire tampon
ENV PYTHONUNBUFFERED=1

# Copie le fichier des dépendances
COPY requirements.txt .

# Installe les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste du contenu
COPY . .

# Commande de lancement
CMD ["python3", "volvo_service.py"]
