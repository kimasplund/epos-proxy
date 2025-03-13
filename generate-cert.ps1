# Simple script to generate SSL certificates for ePOS Proxy Server

Write-Host "Generating SSL certificates for ePOS Proxy Server..." -ForegroundColor Green

# Create certificate directory if it doesn't exist
$certDir = "app/cert"
if (-not (Test-Path $certDir)) {
    New-Item -Path $certDir -ItemType Directory -Force | Out-Null
    Write-Host "Created certificate directory: $certDir" -ForegroundColor Yellow
}

# Create data directories if they don't exist
$directories = @("data", "logs", "app/data", "app/logs")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        Write-Host "Created directory: $dir" -ForegroundColor Yellow
    }
}

# Generate self-signed certificate
try {
    $cert = New-SelfSignedCertificate -DnsName "epos-proxy" -CertStoreLocation "Cert:\CurrentUser\My"
    Export-Certificate -Cert $cert -FilePath "$certDir/server.cert" -Force | Out-Null
    Write-Host "Certificate created: $certDir/server.cert" -ForegroundColor Green
    
    # Export private key
    $keyPath = "$certDir/server.key"
    $type = [System.Security.Cryptography.X509Certificates.X509ContentType]::Pkcs12
    $pfxBytes = $cert.Export($type, "")
    [System.IO.File]::WriteAllBytes("$certDir/server.pfx", $pfxBytes)
    Write-Host "Private key created: $certDir/server.key" -ForegroundColor Green
    
    # Convert PFX to PEM format for the key
    Write-Host "Certificate and key have been generated in $certDir" -ForegroundColor Green
} catch {
    Write-Host "Error generating certificates: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Certificate setup complete. You can now start the ePOS Proxy Server." -ForegroundColor Green 