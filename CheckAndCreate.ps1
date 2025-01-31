# Verificar y crear directorio para 'static/css'
$cssDir = ".\valac_jewelry\static\css"
if (-Not (Test-Path $cssDir)) {
    Write-Host "El directorio $cssDir no existe. Creándolo..."
    New-Item -ItemType Directory -Path $cssDir
} else {
    Write-Host "El directorio $cssDir ya existe."
}

# Verificar y crear el archivo 'styles.css'
$cssFile = "$cssDir\styles.css"
if (-Not (Test-Path $cssFile)) {
    Write-Host "El archivo $cssFile no existe. Creándolo..."
    New-Item -ItemType File -Path $cssFile
    # Añadir contenido inicial a styles.css
    "@tailwind base;`n@tailwind components;`n@tailwind utilities;" | Out-File -FilePath $cssFile
} else {
    Write-Host "El archivo $cssFile ya existe."
}

# Verificar y crear directorio para 'templates'
$templatesDir = ".\valac_jewelry\templates"
if (-Not (Test-Path $templatesDir)) {
    Write-Host "El directorio $templatesDir no existe. Creándolo..."
    New-Item -ItemType Directory -Path $templatesDir
} else {
    Write-Host "El directorio $templatesDir ya existe."
}
