param(
    [string]$KibanaUrl = "http://localhost:5601",
    [string]$SpaceId = "default",
    [string]$ImportPath = "kibana/dashboards.ndjson"
)

$ErrorActionPreference = "Stop"

function Import-KibanaSavedObjects {
    param(
        [Parameter(Mandatory = $true)][string]$TargetUrl,
        [Parameter(Mandatory = $true)][string]$FilePath
    )

    Add-Type -AssemblyName System.Net.Http

    $client = [System.Net.Http.HttpClient]::new()
    $fileStream = $null
    $form = $null
    try {
        $client.DefaultRequestHeaders.Add("kbn-xsrf", "oscorp-phase33")
        $form = [System.Net.Http.MultipartFormDataContent]::new()
        $fileStream = [System.IO.File]::OpenRead($FilePath)
        $fileContent = [System.Net.Http.StreamContent]::new($fileStream)
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/ndjson")
        $form.Add($fileContent, "file", [System.IO.Path]::GetFileName($FilePath))

        $response = $client.PostAsync($TargetUrl, $form).GetAwaiter().GetResult()
        $content = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "Importacion Kibana fallo con HTTP $([int]$response.StatusCode): $content"
        }
        return $content | ConvertFrom-Json
    } finally {
        if ($form) { $form.Dispose() }
        if ($fileStream) { $fileStream.Dispose() }
        $client.Dispose()
    }
}

$fullPath = Join-Path (Get-Location) $ImportPath
if (-not (Test-Path $fullPath)) {
    throw "No existe el archivo de importacion: $fullPath"
}

if ($SpaceId -eq "default") {
    $targetUrl = "$KibanaUrl/api/saved_objects/_import?overwrite=true"
} else {
    $targetUrl = "$KibanaUrl/s/$SpaceId/api/saved_objects/_import?overwrite=true"
}

Write-Host "[kibana:import] Importando $fullPath en space '$SpaceId'..."
$result = Import-KibanaSavedObjects -TargetUrl $targetUrl -FilePath $fullPath
if (-not $result.success) {
    throw "Importacion Kibana sin exito: $($result | ConvertTo-Json -Depth 20)"
}

Write-Host "[kibana:import] Importacion OK."
