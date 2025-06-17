"""
Módulo que contiene listas de términos y palabras que deben ser excluidos 
de la anonimización por categoría de entidad.
"""

# Términos técnicos generales que no deben ser anonimizados independientemente de la entidad
TECH_TERMS = [
    # Frameworks y librerías
    "BootsFaces", "PrimeFaces", "Angular", "Spring", "Bootstrap", "jQuery", 
    "Jasper Reports", "Vuetify", "PrimeNG", "Vue", "React", "JSF", "Java", 
    "Spring Boot", "Spring Cloud", "JPA", "Hibernate", "MyBatis",
    "Angular Material", "Jenkins", "Docker", "Git", "Maven", "Gradle",
    "OAuth2", "JWT", "TypeScript", "HTML5", "CSS3", "Postman", "Swagger",
    "Mockito", "TestNG", "Jasmine", "Scrum", "Agile",
    
    # Conceptos técnicos
    "MVC", "API", "REST", "SOAP", "Clean Architecture", "microservicios",
    "escalables", "eficientes", "interfaces", "backend", "frontend", 
    "base de datos", "bases de datos", "responsivo", "responsive",
    "full stack", "Full Stack", "desarrollador", "Desarrollador",
    "API", "APIs", "integración", "AWS", "usabilidad", "rendimiento",
    "mantenimiento", "arquitectura", "distribuida", "normalización",
    "producción", "preventivo", "correctivo", "sistemas", "aplicaciones",
    "automatización", "Automaticé", "optimización", "transforme", 
    "expectativas", "decisiones", "requisitos", "generación", "reportes",
    "motivación", "innovación", "separación", "protección", "garantizar",
    "diseño", "usabilidad", "testing", "integrando", "desarrollo",
    "endpoints", "navegación", "accesibilidad", "plazos", "existentes",
    "optimicé", "implementé", "modernas", "robustas", "seguras",
    "Diseño Responsivo", "reutilizables", "Avanzado", "Hexagonal",
]

# Términos específicos por tipo de entidad que no deben anonimizarse

# Para entidades tipo PERSON
PERSON_SAFE_TERMS = [
    "Jasper Reports", "Docker", "Jenkins", "Git", "Gradle", "Postman",
    "Desarrollador Full Stack", "Scrum Master", "Tech Lead",
    "Product Owner", "Software Architect", "UX Designer",
    "DevOps Engineer", "QA Engineer", "Team Leader",
    "Desarrollador Backend", "Desarrollador Frontend",
    "Normalización", "Avanzado", "Diseño Responsivo",
    "la toma de decisiones basada en datos",
    "Mi motivación es crear", "distribuida", "y altamente",
    "como OAuth2", "avanzadas", "su diseño", "mejorando su usabilidad y rendimiento",
    "de manera", "Jasmine"
]

# Para entidades tipo LOCATION
LOCATION_SAFE_TERMS = [
    "En el", "el diseño", "la lógica", "plazos",
    "las expectativas del cliente", "el mantenimiento",
    "logrando una arquitectura", "la protección de los datos y",
    "Microservicios"
]

# Para entidades tipo NRP (National Registration Product, número de registro)
NRP_SAFE_TERMS = [
    "Ingeniero", "Profamilia", "sino que transforme la", "Herramientas"
]

# Para entidades tipo IN_PAN (números de tarjeta)
PAN_SAFE_TERMS = [
    "BootsFaces", "PrimeFaces", "escalables", "eficientes", "desarrollé", 
    "integrando", "soluciones", "incluyendo", "generación", "decisiones", 
    "profundizo", "Artificial", "innovación", "motivación", "requisitos",
    "transforme", "navegación", "Desarrollé", "interfaces", "Implementé",
    "Planifiqué", "Profamilia", "Septiembre", "desarrollo", "Desarrollé",
    "aplicación", "utilizando", "PrimeFaces", "interfaces", "Implementé",
    "desarrollé", "interfaces", "utilizando", "usabilidad", "responsivo",
    "eficiencia", "cumpliendo", "asegurando", "soluciones", "Implementé",
    "separación", "utilizando", "Desarrollé", "mecanismos", "garantizar", 
    "protección", "Desarrollé", "interfaces", "integrando", "existentes",
    "utilizando", "PrimeFaces", "BootsFaces", "usabilidad", "Automaticé",
    "generación", "utilizando", "detallados", "generación", "correctivo",
    "preventivo", "asegurando", "producción"
]

# Para entidades tipo DATE_TIME
DATETIME_SAFE_TERMS = [
    "2021", "Abril - 2022", "2022", "Septiembre",
    "2023", "2023", "Noviembre"
]

# Para entidades tipo URL
URL_SAFE_TERMS = [
    "gmail.com" # Solo si no está precedido por un nombre o identificador personal
]

# Configuración de umbrales de confianza por tipo de entidad
CONFIDENCE_THRESHOLDS = {
    "DEFAULT": 0.7,   # Umbral predeterminado para cualquier entidad
    "PERSON": 0.9,    # Más estricto para nombres de personas
    "IN_PAN": 0.4,    # Más estricto para números de tarjetas
    "LOCATION": 0.9,  # Más estricto para ubicaciones
    "NRP": 0.9,       # Más estricto para números de registro personal
    "US_DRIVER_LICENSE": 0.5,  # Para licencias de conducir
    "US_BANK_NUMBER": 0.5,     # Para números de cuenta bancaria
    "URL": 0.7,                # Para URLs
    "EMAIL_ADDRESS": 0.95      # Para direcciones de correo (alto para estar seguros)
}

# Patrones regex específicos por tipo de entidad para filtrar falsos positivos
REGEX_FILTERS = {
    "IN_PAN": r'\d{6,}',  # Debe tener al menos 6 dígitos consecutivos
    "PERSON": r'^[A-Z][a-z]+(\s[A-Z][a-z]+)+$',  # Formato de nombre típico
    "LOCATION": r'^(el|la|los|las|en el|en la|en los|en las)\s'  # Frases comunes incorrectas
}

# Organizaciones y entidades conocidas (empresas, productos, etc.)
ORGANIZATIONS = [
    "Profamilia", 
    "Gencell Genética avanzada", 
    "Microsoft", 
    "Google", 
    "Amazon", 
    "Oracle",
    "IBM"
]
