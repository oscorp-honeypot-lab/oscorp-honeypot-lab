param(
    [string]$KibanaUrl = "http://localhost:5601",
    [string]$ElasticsearchUrl = "http://localhost:9200",
    [string]$EventsIndexName = "cowrie-events",
    [string]$RiskIndexName = "oscorp-session-risk",
    [string]$ExportPath = "kibana/dashboards.ndjson"
)

$ErrorActionPreference = "Stop"

$Headers = @{
    "kbn-xsrf" = "oscorp-phase33"
}

function Invoke-KibanaJson {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        [object]$Body = $null
    )

    $uri = "$KibanaUrl$Path"
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $Headers -TimeoutSec 30
    }

    return Invoke-RestMethod `
        -Method $Method `
        -Uri $uri `
        -Headers $Headers `
        -ContentType "application/json" `
        -Body (ConvertTo-Json -InputObject $Body -Depth 80) `
        -TimeoutSec 30
}

function Invoke-ElasticsearchJson {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        [object]$Body = $null
    )

    $uri = "$ElasticsearchUrl$Path"
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $uri -TimeoutSec 30
    }

    return Invoke-RestMethod `
        -Method $Method `
        -Uri $uri `
        -ContentType "application/json" `
        -Body (ConvertTo-Json -InputObject $Body -Depth 80) `
        -TimeoutSec 30
}

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

Write-Host "[kibana:fase33] Verificando estado de Kibana..."
$status = Invoke-KibanaJson -Method "Get" -Path "/api/status"
if ($status.status.overall.level -ne "available") {
    throw "Kibana no esta disponible: $($status.status.overall.level)"
}

Write-Host "[kibana:fase33] Verificando indices analiticos..."
$riskCount = Invoke-ElasticsearchJson -Method "Get" -Path "/$RiskIndexName/_count"
if ($riskCount.count -lt 1) {
    throw "El indice $RiskIndexName no contiene documentos."
}

$eventsMapping = Invoke-ElasticsearchJson -Method "Get" -Path "/$EventsIndexName/_mapping"
$properties = $eventsMapping.$EventsIndexName.mappings.properties
if (-not $properties.PSObject.Properties.Name.Contains("src_location")) {
    throw "Falta src_location en el mapping de $EventsIndexName."
}
if ($properties.src_location.type -ne "geo_point") {
    throw "src_location no es geo_point."
}

$riskAggs = Invoke-ElasticsearchJson -Method "Post" -Path "/$RiskIndexName/_search" -Body @{
    size = 0
    aggs = @{
        risk_levels = @{ terms = @{ field = "risk_level"; size = 4 } }
        risk_score = @{ stats = @{ field = "risk_score" } }
        high_or_critical = @{
            filter = @{
                terms = @{
                    risk_level = @("high", "critical")
                }
            }
        }
    }
}
if (@($riskAggs.aggregations.risk_levels.buckets).Count -lt 1) {
    throw "No hay buckets de riesgo para las visualizaciones."
}

$geoCount = Invoke-ElasticsearchJson -Method "Post" -Path "/$EventsIndexName/_count" -Body @{
    query = @{
        exists = @{
            field = "src_location"
        }
    }
}

Write-Host "[kibana:fase33] Verificando objetos guardados..."
$requiredObjects = @(
    @{ type = "dashboard"; id = "oscorp-phase33-analytics" },
    @{ type = "visualization"; id = "oscorp-phase33-risk-distribution" },
    @{ type = "visualization"; id = "oscorp-phase33-risk-score-histogram" },
    @{ type = "visualization"; id = "oscorp-phase33-high-risk-count" },
    @{ type = "search"; id = "oscorp-phase33-high-risk-sessions" },
    @{ type = "map"; id = "oscorp-phase33-attack-origin-map" }
)

foreach ($object in $requiredObjects) {
    $savedObject = Invoke-KibanaJson -Method "Get" -Path "/api/saved_objects/$($object.type)/$($object.id)"
    if ($savedObject.id -ne $object.id) {
        throw "No se pudo validar $($object.type)/$($object.id)."
    }
}

$dashboard = Invoke-KibanaJson -Method "Get" -Path "/api/saved_objects/dashboard/oscorp-phase33-analytics"
$parsedPanels = $dashboard.attributes.panelsJSON | ConvertFrom-Json
if ($parsedPanels.PSObject.Properties.Name -contains "value") {
    $panels = @($parsedPanels.value)
} else {
    $panels = @($parsedPanels)
}
if ($panels.Count -lt 5) {
    throw "El dashboard analitico tiene menos paneles de los esperados."
}

Write-Host "[kibana:fase33] Verificando export versionado..."
$fullExportPath = Join-Path (Get-Location) $ExportPath
if (-not (Test-Path $fullExportPath)) {
    throw "No existe $fullExportPath."
}
$exportText = Get-Content -Raw $fullExportPath
foreach ($id in @("oscorp-phase32-operational", "oscorp-phase33-analytics", "oscorp-phase33-attack-origin-map")) {
    if ($exportText -notmatch [regex]::Escape($id)) {
        throw "El export no contiene $id."
    }
}

Write-Host "[kibana:fase33] Importando export en un space limpio..."
$spaceId = "oscorp-phase33-clean-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$spaceCreated = $false
try {
    Invoke-KibanaJson -Method "Post" -Path "/api/spaces/space" -Body @{
        id = $spaceId
        name = "OSCORP Phase 33 Clean Validation"
        disabledFeatures = @()
    } | Out-Null
    $spaceCreated = $true

    $importResult = Import-KibanaSavedObjects `
        -TargetUrl "$KibanaUrl/s/$spaceId/api/saved_objects/_import?overwrite=true" `
        -FilePath $fullExportPath
    if (-not $importResult.success) {
        throw "Importacion en space limpio sin exito: $($importResult | ConvertTo-Json -Depth 20)"
    }

    $importedDashboards = Invoke-KibanaJson -Method "Get" -Path "/s/$spaceId/api/saved_objects/_find?type=dashboard&per_page=100"
    foreach ($dashboard in @(
        @{ id = "oscorp-phase32-operational"; title = "OSCORP - Dashboard operativo" },
        @{ id = "oscorp-phase33-analytics"; title = "OSCORP - Dashboard analitico" }
    )) {
        $match = @($importedDashboards.saved_objects) | Where-Object {
            $_.id -eq $dashboard.id -or
            $_.originId -eq $dashboard.id -or
            $_.attributes.title -eq $dashboard.title
        } | Select-Object -First 1
        if (-not $match) {
            throw "No se importo $($dashboard.id) en $spaceId."
        }
    }
} finally {
    if ($spaceCreated) {
        Invoke-KibanaJson -Method "Delete" -Path "/api/spaces/space/$spaceId" | Out-Null
    }
}

Write-Host "[kibana:fase33] Validacion OK."
Write-Host "[kibana:fase33] Risk docs: $($riskCount.count)"
Write-Host "[kibana:fase33] High/Critical docs: $($riskAggs.aggregations.high_or_critical.doc_count)"
Write-Host "[kibana:fase33] Geo docs con src_location: $($geoCount.count)"
Write-Host "[kibana:fase33] Export: $fullExportPath"
Write-Host "[kibana:fase33] Dashboard: $KibanaUrl/app/dashboards#/view/oscorp-phase33-analytics"
