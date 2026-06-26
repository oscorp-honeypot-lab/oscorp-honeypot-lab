param(
    [string]$KibanaUrl = "http://localhost:5601",
    [string]$ElasticsearchUrl = "http://localhost:9200",
    [string]$IndexName = "cowrie-events"
)

$ErrorActionPreference = "Stop"

$Headers = @{
    "kbn-xsrf" = "oscorp-phase32"
}

function Invoke-KibanaJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    return Invoke-RestMethod -Method Get -Uri "$KibanaUrl$Path" -Headers $Headers -TimeoutSec 30
}

function Invoke-ElasticsearchJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [object]$Body = $null
    )

    if ($null -eq $Body) {
        return Invoke-RestMethod -Method Get -Uri "$ElasticsearchUrl$Path" -TimeoutSec 30
    }

    return Invoke-RestMethod `
        -Method Post `
        -Uri "$ElasticsearchUrl$Path" `
        -ContentType "application/json" `
        -Body (ConvertTo-Json -InputObject $Body -Depth 50) `
        -TimeoutSec 30
}

Write-Host "[kibana:fase32] Verificando estado de Kibana..."
$status = Invoke-KibanaJson -Path "/api/status"
if ($status.status.overall.level -ne "available") {
    throw "Kibana no esta disponible: $($status.status.overall.level)"
}

Write-Host "[kibana:fase32] Verificando indice y mapping..."
$count = Invoke-ElasticsearchJson -Path "/$IndexName/_count"
if ($count.count -lt 1) {
    throw "El indice $IndexName no contiene documentos."
}

$mapping = Invoke-ElasticsearchJson -Path "/$IndexName/_mapping"
$properties = $mapping.$IndexName.mappings.properties
foreach ($field in @("timestamp_evento", "eventid", "session_id", "src_ip", "username")) {
    if (-not $properties.PSObject.Properties.Name.Contains($field)) {
        throw "Falta el campo requerido '$field' en $IndexName."
    }
}

Write-Host "[kibana:fase32] Verificando data view..."
$dataViewFind = Invoke-KibanaJson -Path "/api/saved_objects/_find?type=index-pattern&search_fields=title&search=$IndexName&per_page=100"
$dataView = @($dataViewFind.saved_objects) | Where-Object { $_.attributes.title -eq $IndexName } | Select-Object -First 1
if (-not $dataView) {
    throw "No existe data view para $IndexName."
}
if ($dataView.attributes.timeFieldName -ne "timestamp_evento") {
    throw "El data view usa un campo temporal inesperado: $($dataView.attributes.timeFieldName)"
}

Write-Host "[kibana:fase32] Verificando objetos guardados..."
$requiredObjects = @(
    @{ type = "dashboard"; id = "oscorp-phase32-operational" },
    @{ type = "visualization"; id = "oscorp-phase32-total-events" },
    @{ type = "visualization"; id = "oscorp-phase32-events-timeline" },
    @{ type = "visualization"; id = "oscorp-phase32-events-by-type" },
    @{ type = "visualization"; id = "oscorp-phase32-sessions-table" },
    @{ type = "visualization"; id = "oscorp-phase32-src-ip-table" },
    @{ type = "search"; id = "oscorp-phase32-operational-events" }
)

foreach ($object in $requiredObjects) {
    $savedObject = Invoke-KibanaJson -Path "/api/saved_objects/$($object.type)/$($object.id)"
    if ($savedObject.id -ne $object.id) {
        throw "No se pudo validar $($object.type)/$($object.id)."
    }
}

$dashboard = Invoke-KibanaJson -Path "/api/saved_objects/dashboard/oscorp-phase32-operational"
$panels = $dashboard.attributes.panelsJSON | ConvertFrom-Json
$panels = @($panels)
if ($panels.Count -eq 1 -and $panels[0] -is [System.Array]) {
    $panels = @($panels[0])
}
if (@($panels).Count -lt 6) {
    throw "El dashboard operativo tiene menos paneles de los esperados."
}

Write-Host "[kibana:fase32] Validando consultas base de los paneles..."
$aggregations = Invoke-ElasticsearchJson -Path "/$IndexName/_search" -Body @{
    size = 0
    aggs = @{
        sessions = @{ cardinality = @{ field = "session_id" } }
        event_types = @{ terms = @{ field = "eventid"; size = 5 } }
        sources = @{ terms = @{ field = "src_ip"; size = 5 } }
        timeline = @{
            date_histogram = @{
                field = "timestamp_evento"
                fixed_interval = "1h"
                min_doc_count = 1
            }
        }
    }
}

if ($aggregations.aggregations.sessions.value -lt 1) {
    throw "No hay sesiones agregables en $IndexName."
}
if (@($aggregations.aggregations.event_types.buckets).Count -lt 1) {
    throw "No hay buckets de eventid para los paneles operativos."
}
if (@($aggregations.aggregations.timeline.buckets).Count -lt 1) {
    throw "No hay buckets temporales para evolucion de eventos."
}

Write-Host "[kibana:fase32] Validacion OK."
Write-Host "[kibana:fase32] Documentos: $($count.count)"
Write-Host "[kibana:fase32] Data view: $($dataView.id)"
Write-Host "[kibana:fase32] Dashboard: $KibanaUrl/app/dashboards#/view/oscorp-phase32-operational"
