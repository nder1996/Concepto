# Reconocedores Personalizados

Los reconocedores personalizados utilizados en la aplicación se han centralizado en el módulo `src.services.presidio.recognizers`.

**Para utilizar los reconocedores, importarlos desde este módulo centralizado:**

```python
from src.services.presidio.recognizers import EmailRecognizer, PhoneRecognizer, ColombianIDRecognizer
```

## Reconocedores Disponibles

Los reconocedores centralizados incluyen:

1. **EmailRecognizer** - Para direcciones de correo electrónico
2. **PhoneRecognizer** - Para números telefónicos colombianos e internacionales
3. **ColombianIDRecognizer** - Para documentos de identidad colombianos (CC, TI, CE, RC, etc.)
4. **FlairContextValidator** - (Opcional) Para validación de entidades usando Flair
