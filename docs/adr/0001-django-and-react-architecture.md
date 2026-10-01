# Arquitectura Backend en Django y Dashboard en React

Para gestionar la ingesta periódica de datos de la API de Clash Royale, persistencia relacional y gobernanza de clanes, se implementará un backend con Django (Django REST Framework y tareas programadas) junto con una base de datos PostgreSQL y una interfaz web desacoplada en React. Esta arquitectura separa limpiamente el dominio y las tareas de fondo (ingesta, evaluación de reglas, alertas a bots) de la capa visual de auditoría y configuración para líderes.
