# Nouveau rapport HEPIA - Créateur de structure LaTeX
# Placer ce script dans le dossier parent des rapports

$ErrorActionPreference = "Stop"

# Demander le nom du rapport
Add-Type -AssemblyName Microsoft.VisualBasic
$reportName = [Microsoft.VisualBasic.Interaction]::InputBox(
    "Entrer le nom du nouveau rapport :",
    "Nouveau rapport LaTeX",
    "NomRapport"
)

if ([string]::IsNullOrWhiteSpace($reportName)) {
    [System.Windows.Forms.MessageBox]::Show("Aucun nom saisi. Annulation.", "Annulé")
    exit
}

# Nettoyer le nom (pas d'espaces, pas de caractères interdits)
$reportName = $reportName.Trim()
$reportName = $reportName -replace '[\\/:*?"<>|]', '_'

# Chemin de base = dossier du script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$reportDir = Join-Path $scriptDir $reportName
$imagesDir = Join-Path $reportDir "Images"
$outDir    = Join-Path $reportDir "out"

# Vérifier que le dossier n'existe pas déjà
if (Test-Path $reportDir) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Le dossier '$reportName' existe déjà !",
        "Erreur",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    exit
}

# Créer la structure
New-Item -ItemType Directory -Path $reportDir  | Out-Null
New-Item -ItemType Directory -Path $imagesDir  | Out-Null
New-Item -ItemType Directory -Path $outDir     | Out-Null

# Copier le logo hepia depuis le dossier du script
$logoSrc = Join-Path $scriptDir "hepia_simple.png"
if (Test-Path $logoSrc) {
    Copy-Item $logoSrc -Destination (Join-Path $imagesDir "hepia_simple.png")
} else {
    Write-Warning "Logo hepia_simple.png introuvable à côté du script. Placer le logo manuellement dans Images\"
}

# Générer le fichier .tex avec le nom du rapport
$texPath = Join-Path $reportDir "$reportName.tex"
$texTemplate = Get-Content -Path (Join-Path $scriptDir "template.tex") -Raw -Encoding UTF8
$texContent = $texTemplate -replace 'TITRE DU RAPPORT', $reportName
[System.IO.File]::WriteAllText($texPath, $texContent, [System.Text.Encoding]::UTF8)

# Confirmer
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show(
    "Rapport '$reportName' créé avec succès !`n`n$reportDir",
    "Succès",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
)

# Ouvrir le dossier dans l'explorateur
Start-Process explorer.exe -ArgumentList $reportDir