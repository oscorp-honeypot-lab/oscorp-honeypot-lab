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

function ConvertTo-CompactJson {
    param([Parameter(Mandatory = $true)]$Value)
    return ConvertTo-Json -InputObject $Value -Depth 80 -Compress
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

function Test-ElasticsearchIndexExists {
    param([Parameter(Mandatory = $true)][string]$IndexName)

    try {
        Invoke-RestMethod -Method Get -Uri "$ElasticsearchUrl/$IndexName" -TimeoutSec 30 | Out-Null
        return $true
    } catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 404) {
            return $false
        }
        throw
    }
}

function Ensure-EventsGeoMapping {
    Write-Host "[kibana:fase33] Verificando mapping geo_point en $EventsIndexName..."
    $mapping = Invoke-ElasticsearchJson -Method "Get" -Path "/$EventsIndexName/_mapping"
    $properties = $mapping.$EventsIndexName.mappings.properties
    if ($properties.PSObject.Properties.Name.Contains("src_location")) {
        if ($properties.src_location.type -ne "geo_point") {
            throw "src_location existe pero no es geo_point en $EventsIndexName."
        }
        return
    }

    Invoke-ElasticsearchJson -Method "Put" -Path "/$EventsIndexName/_mapping" -Body @{
        properties = @{
            src_location = @{
                type = "geo_point"
            }
        }
    } | Out-Null
    Write-Host "[kibana:fase33] Mapping src_location geo_point agregado."
}

function Ensure-RiskIndex {
    Write-Host "[kibana:fase33] Preparando indice analitico $RiskIndexName..."
    $mapping = @{
        mappings = @{
            properties = @{
                session_key = @{ type = "keyword" }
                session_id = @{ type = "keyword" }
                sensor = @{ type = "keyword" }
                src_ip = @{ type = "ip" }
                src_port = @{ type = "integer" }
                first_event_at = @{ type = "date" }
                last_event_at = @{ type = "date" }
                duration_seconds = @{ type = "float" }
                lifecycle_status = @{ type = "keyword" }
                event_count = @{ type = "integer" }
                login_success_count = @{ type = "integer" }
                login_failed_count = @{ type = "integer" }
                command_count = @{ type = "integer" }
                command_failed_count = @{ type = "integer" }
                download_count = @{ type = "integer" }
                first_username = @{ type = "keyword" }
                last_username = @{ type = "keyword" }
                has_successful_login = @{ type = "boolean" }
                has_download = @{ type = "boolean" }
                reviewed = @{ type = "boolean" }
                risk_score = @{ type = "integer" }
                risk_level = @{ type = "keyword" }
                rules_version = @{ type = "keyword" }
                reasons = @{ type = "object"; enabled = $false }
                calculated_at = @{ type = "date" }
            }
        }
    }

    if (-not (Test-ElasticsearchIndexExists -IndexName $RiskIndexName)) {
        Invoke-ElasticsearchJson -Method "Put" -Path "/$RiskIndexName" -Body $mapping | Out-Null
        Write-Host "[kibana:fase33] Indice $RiskIndexName creado."
    } else {
        Invoke-ElasticsearchJson -Method "Put" -Path "/$RiskIndexName/_mapping" -Body $mapping.mappings | Out-Null
    }
}

function Sync-RiskIndex {
    Write-Host "[kibana:fase33] Sincronizando risk scores desde PostgreSQL a Elasticsearch..."
    $query = @"
WITH latest_risk AS (
    SELECT DISTINCT ON (session_key)
        session_key,
        rules_version,
        score,
        risk_level,
        reasons,
        calculated_at
    FROM session_risk_scores
    ORDER BY session_key, calculated_at DESC, id DESC
)
SELECT jsonb_build_object(
    'session_key', s.session_key,
    'session_id', s.session_id,
    'sensor', s.sensor,
    'src_ip', NULLIF(s.src_ip, ''),
    'src_port', s.src_port,
    'first_event_at', s.first_event_at,
    'last_event_at', s.last_event_at,
    'duration_seconds', s.duration_seconds,
    'lifecycle_status', s.lifecycle_status,
    'event_count', s.event_count,
    'login_success_count', s.login_success_count,
    'login_failed_count', s.login_failed_count,
    'command_count', s.command_count,
    'command_failed_count', s.command_failed_count,
    'download_count', s.download_count,
    'first_username', s.first_username,
    'last_username', s.last_username,
    'has_successful_login', s.has_successful_login,
    'has_download', s.has_download,
    'reviewed', s.reviewed,
    'risk_score', r.score,
    'risk_level', r.risk_level,
    'rules_version', r.rules_version,
    'reasons', r.reasons,
    'calculated_at', r.calculated_at
)::text
FROM sessions s
JOIN latest_risk r ON r.session_key = s.session_key
ORDER BY s.last_event_at DESC, s.session_key;
"@

    $rows = & docker compose exec -T postgres psql -U oscorp -d oscorp -Atc $query
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo leer session_risk_scores desde PostgreSQL."
    }
    $rows = @($rows) | Where-Object { $_ -and $_.Trim() }
    if ($rows.Count -lt 1) {
        throw "No hay risk scores para sincronizar."
    }

    Invoke-ElasticsearchJson -Method "Post" -Path "/$RiskIndexName/_delete_by_query?conflicts=proceed&refresh=true" -Body @{
        query = @{ match_all = @{} }
    } | Out-Null

    $bulkLines = New-Object System.Collections.Generic.List[string]
    foreach ($row in $rows) {
        $doc = $row | ConvertFrom-Json
        $bulkLines.Add((ConvertTo-CompactJson @{ index = @{ _index = $RiskIndexName; _id = $doc.session_key } }))
        $bulkLines.Add($row)
    }

    $bulkBody = ($bulkLines -join "`n") + "`n"
    $bulk = Invoke-RestMethod `
        -Method Post `
        -Uri "$ElasticsearchUrl/_bulk?refresh=true" `
        -ContentType "application/x-ndjson" `
        -Body $bulkBody `
        -TimeoutSec 60

    if ($bulk.errors) {
        $firstError = @($bulk.items | Where-Object { $_.index.error } | Select-Object -First 1)
        throw "El bulk de $RiskIndexName fallo: $($firstError.index.error.reason)"
    }

    Write-Host "[kibana:fase33] Sesiones sincronizadas: $($rows.Count)"
}

function Get-OrCreateDataView {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$TimeField
    )

    $encodedTitle = [System.Uri]::EscapeDataString($Title)
    $result = Invoke-KibanaJson -Method "Get" -Path "/api/saved_objects/_find?type=index-pattern&search_fields=title&search=$encodedTitle&per_page=100"
    $existing = @($result.saved_objects) | Where-Object { $_.attributes.title -eq $Title } | Select-Object -First 1
    if ($existing) {
        Write-Host "[kibana:fase33] Data view existente: $Title ($($existing.id))"
        return $existing.id
    }

    $created = Invoke-KibanaJson -Method "Post" -Path "/api/data_views/data_view" -Body @{
        data_view = @{
            title = $Title
            name = $Name
            timeFieldName = $TimeField
        }
        override = $true
    }
    Write-Host "[kibana:fase33] Data view creado: $Title ($($created.data_view.id))"
    return $created.data_view.id
}

function New-SearchSource {
    param(
        [string]$Query = "",
        [string]$RefName = "kibanaSavedObjectMeta.searchSourceJSON.index"
    )

    return @{
        query = @{
            language = "kuery"
            query = $Query
        }
        filter = @()
        indexRefName = $RefName
    }
}

function Set-Visualization {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)]$VisState,
        [Parameter(Mandatory = $true)][string]$DataViewId,
        [string]$Query = ""
    )

    $body = @{
        attributes = @{
            title = $Title
            description = $Description
            visState = ConvertTo-CompactJson $VisState
            uiStateJSON = "{}"
            kibanaSavedObjectMeta = @{
                searchSourceJSON = ConvertTo-CompactJson (New-SearchSource -Query $Query)
            }
        }
        references = @(
            @{
                name = "kibanaSavedObjectMeta.searchSourceJSON.index"
                type = "index-pattern"
                id = $DataViewId
            }
        )
    }

    Invoke-KibanaJson -Method "Post" -Path "/api/saved_objects/visualization/$Id`?overwrite=true" -Body $body | Out-Null
    Write-Host "[kibana:fase33] Visualizacion lista: $Title"
}

function Set-RiskVisualizations {
    param([Parameter(Mandatory = $true)][string]$RiskDataViewId)

    Set-Visualization `
        -Id "oscorp-phase33-risk-distribution" `
        -Title "OSCORP - Distribucion de riesgo" `
        -Description "Sesiones agrupadas por nivel de riesgo calculado." `
        -DataViewId $RiskDataViewId `
        -VisState @{
            title = "OSCORP - Distribucion de riesgo"
            type = "histogram"
            params = @{
                type = "histogram"
                grid = @{ categoryLines = $false }
                categoryAxes = @(
                    @{
                        id = "CategoryAxis-1"
                        type = "category"
                        position = "bottom"
                        show = $true
                        style = @{}
                        scale = @{ type = "linear" }
                        labels = @{ show = $true; filter = $false; truncate = 100 }
                        title = @{}
                    }
                )
                valueAxes = @(
                    @{
                        id = "ValueAxis-1"
                        name = "LeftAxis-1"
                        type = "value"
                        position = "left"
                        show = $true
                        style = @{}
                        scale = @{ type = "linear"; mode = "normal" }
                        labels = @{ show = $true; rotate = 0; filter = $false; truncate = 100 }
                        title = @{ text = "Sesiones" }
                    }
                )
                seriesParams = @(
                    @{
                        show = $true
                        type = "histogram"
                        mode = "normal"
                        data = @{ label = "Sesiones"; id = "1" }
                        valueAxis = "ValueAxis-1"
                        drawLinesBetweenPoints = $true
                        showCircles = $true
                    }
                )
                addTooltip = $true
                addLegend = $false
                legendPosition = "right"
                times = @()
                addTimeMarker = $false
            }
            aggs = @(
                @{ id = "1"; enabled = $true; type = "count"; schema = "metric"; params = @{} },
                @{
                    id = "2"
                    enabled = $true
                    type = "terms"
                    schema = "segment"
                    params = @{
                        field = "risk_level"
                        orderBy = "1"
                        order = "desc"
                        size = 4
                        otherBucket = $false
                        missingBucket = $false
                    }
                }
            )
        }

    Set-Visualization `
        -Id "oscorp-phase33-risk-score-histogram" `
        -Title "OSCORP - Histograma de score" `
        -Description "Distribucion del Attack Risk Score por sesion." `
        -DataViewId $RiskDataViewId `
        -VisState @{
            title = "OSCORP - Histograma de score"
            type = "histogram"
            params = @{
                type = "histogram"
                grid = @{ categoryLines = $false }
                categoryAxes = @(
                    @{
                        id = "CategoryAxis-1"
                        type = "category"
                        position = "bottom"
                        show = $true
                        style = @{}
                        scale = @{ type = "linear" }
                        labels = @{ show = $true; filter = $false; truncate = 100 }
                        title = @{}
                    }
                )
                valueAxes = @(
                    @{
                        id = "ValueAxis-1"
                        name = "LeftAxis-1"
                        type = "value"
                        position = "left"
                        show = $true
                        style = @{}
                        scale = @{ type = "linear"; mode = "normal" }
                        labels = @{ show = $true; rotate = 0; filter = $false; truncate = 100 }
                        title = @{ text = "Sesiones" }
                    }
                )
                seriesParams = @(
                    @{
                        show = $true
                        type = "histogram"
                        mode = "normal"
                        data = @{ label = "Sesiones"; id = "1" }
                        valueAxis = "ValueAxis-1"
                        drawLinesBetweenPoints = $true
                        showCircles = $true
                    }
                )
                addTooltip = $true
                addLegend = $false
                legendPosition = "right"
                times = @()
                addTimeMarker = $false
            }
            aggs = @(
                @{ id = "1"; enabled = $true; type = "count"; schema = "metric"; params = @{} },
                @{
                    id = "2"
                    enabled = $true
                    type = "histogram"
                    schema = "segment"
                    params = @{
                        field = "risk_score"
                        interval = 10
                        min_doc_count = 1
                        extended_bounds = @{}
                    }
                }
            )
        }

    Set-Visualization `
        -Id "oscorp-phase33-high-risk-count" `
        -Title "OSCORP - Sesiones high critical" `
        -Description "Cantidad de sesiones con riesgo high o critical." `
        -DataViewId $RiskDataViewId `
        -Query "risk_level: high or risk_level: critical" `
        -VisState @{
            title = "OSCORP - Sesiones high critical"
            type = "metric"
            params = @{
                addTooltip = $true
                addLegend = $false
                type = "metric"
                metric = @{
                    percentageMode = $false
                    useRanges = $false
                    colorSchema = "Green to Red"
                    metricColorMode = "None"
                    labels = @{ show = $true }
                    invertColors = $false
                    style = @{
                        bgFill = "#000"
                        bgColor = $false
                        labelColor = $false
                        subText = "high/critical"
                        fontSize = 60
                    }
                }
            }
            aggs = @(
                @{ id = "1"; enabled = $true; type = "count"; schema = "metric"; params = @{} }
            )
        }
}

function Set-HighRiskSearch {
    param([Parameter(Mandatory = $true)][string]$RiskDataViewId)

    $searchSource = New-SearchSource -Query "risk_level: high or risk_level: critical"
    $searchSource.sort = @(
        @{
            risk_score = @{
                order = "desc"
                unmapped_type = "boolean"
            }
        }
    )

    $body = @{
        attributes = @{
            title = "OSCORP - Sesiones de mayor riesgo"
            description = "Tabla importable de sesiones con score alto para investigacion."
            columns = @("last_event_at", "risk_level", "risk_score", "session_key", "src_ip", "last_username", "event_count", "command_count", "download_count")
            sort = @(@("risk_score", "desc"))
            kibanaSavedObjectMeta = @{
                searchSourceJSON = ConvertTo-CompactJson $searchSource
            }
        }
        references = @(
            @{
                name = "kibanaSavedObjectMeta.searchSourceJSON.index"
                type = "index-pattern"
                id = $RiskDataViewId
            }
        )
    }

    Invoke-KibanaJson -Method "Post" -Path "/api/saved_objects/search/oscorp-phase33-high-risk-sessions`?overwrite=true" -Body $body | Out-Null
    Write-Host "[kibana:fase33] Tabla analitica lista: OSCORP - Sesiones de mayor riesgo"
}

function Set-AttackOriginMap {
    param([Parameter(Mandatory = $true)][string]$EventsDataViewId)

    $layerList = @(
        @{
            id = "oscorp-phase33-origin-layer"
            label = "Origen de ataques SSH"
            minZoom = 0
            maxZoom = 24
            alpha = 0.75
            visible = $true
            type = "ES_SEARCH"
            sourceDescriptor = @{
                id = "oscorp-phase33-origin-source"
                type = "ES_SEARCH"
                indexPatternId = $EventsDataViewId
                geoField = "src_location"
                scalingType = "LIMIT"
                tooltipProperties = @("src_ip", "eventid", "username", "sensor", "timestamp_evento")
                filterByMapBounds = $true
            }
            style = @{
                type = "VECTOR"
                properties = @{
                    fillColor = @{ type = "STATIC"; options = @{ color = "#D36086" } }
                    lineColor = @{ type = "STATIC"; options = @{ color = "#D36086" } }
                    lineWidth = @{ type = "STATIC"; options = @{ size = 1 } }
                    iconSize = @{ type = "STATIC"; options = @{ size = 6 } }
                    labelText = @{ type = "STATIC"; options = @{ value = "" } }
                }
            }
            joins = @()
        }
    )

    $mapState = @{
        zoom = 2
        center = @{ lon = 0; lat = 20 }
        timeFilters = @{ from = "now-30d"; to = "now" }
        refreshConfig = @{ isPaused = $true; interval = 0 }
        query = @{ language = "kuery"; query = "" }
        filters = @()
        settings = @{
            autoFitToDataBounds = $true
            hideToolbarOverlay = $false
            fixedLocation = $false
            browserLocation = @{ zoom = 2; center = @{ lon = 0; lat = 20 } }
        }
    }

    $body = @{
        attributes = @{
            title = "OSCORP - Mapa geografico de ataques"
            description = "Mapa importable sobre src_location. En LAB puede quedar sin puntos porque las IPs son privadas."
            layerListJSON = ConvertTo-CompactJson -Value $layerList
            mapStateJSON = ConvertTo-CompactJson -Value $mapState
            uiStateJSON = "{}"
        }
        references = @(
            @{
                name = "oscorp-phase33-origin-source.indexPattern"
                type = "index-pattern"
                id = $EventsDataViewId
            }
        )
    }

    Invoke-KibanaJson -Method "Post" -Path "/api/saved_objects/map/oscorp-phase33-attack-origin-map`?overwrite=true" -Body $body | Out-Null
    Write-Host "[kibana:fase33] Mapa listo: OSCORP - Mapa geografico de ataques"
}

function Set-AnalyticsDashboard {
    $panelDefinitions = @(
        @{ name = "panel_1"; type = "visualization"; id = "oscorp-phase33-high-risk-count"; x = 0; y = 0; w = 10; h = 8 },
        @{ name = "panel_2"; type = "visualization"; id = "oscorp-phase33-risk-distribution"; x = 10; y = 0; w = 19; h = 8 },
        @{ name = "panel_3"; type = "visualization"; id = "oscorp-phase33-risk-score-histogram"; x = 29; y = 0; w = 19; h = 8 },
        @{ name = "panel_4"; type = "search"; id = "oscorp-phase33-high-risk-sessions"; x = 0; y = 8; w = 24; h = 13 },
        @{ name = "panel_5"; type = "map"; id = "oscorp-phase33-attack-origin-map"; x = 24; y = 8; w = 24; h = 13 }
    )

    $panels = @()
    $references = @()
    $index = 1
    foreach ($panel in $panelDefinitions) {
        $panels += @{
            version = "8.13.4"
            type = $panel.type
            gridData = @{
                x = $panel.x
                y = $panel.y
                w = $panel.w
                h = $panel.h
                i = "$index"
            }
            panelIndex = "$index"
            embeddableConfig = @{}
            panelRefName = $panel.name
        }
        $references += @{
            name = $panel.name
            type = $panel.type
            id = $panel.id
        }
        $index++
    }

    $body = @{
        attributes = @{
            title = "OSCORP - Dashboard analitico"
            description = "Fase 33 - riesgo versionado y mapa geografico importables."
            panelsJSON = ConvertTo-CompactJson -Value $panels
            optionsJSON = ConvertTo-CompactJson @{
                useMargins = $true
                syncColors = $false
                syncCursor = $true
                syncTooltips = $true
                hidePanelTitles = $false
            }
            timeRestore = $true
            timeFrom = "now-30d"
            timeTo = "now"
            kibanaSavedObjectMeta = @{
                searchSourceJSON = ConvertTo-CompactJson @{
                    query = @{ language = "kuery"; query = "" }
                    filter = @()
                }
            }
        }
        references = $references
    }

    Invoke-KibanaJson -Method "Post" -Path "/api/saved_objects/dashboard/oscorp-phase33-analytics`?overwrite=true" -Body $body | Out-Null
    Write-Host "[kibana:fase33] Dashboard listo: OSCORP - Dashboard analitico"
}

function Export-Dashboards {
    Write-Host "[kibana:fase33] Exportando objetos versionados a $ExportPath..."
    $exportFullPath = Join-Path (Get-Location) $ExportPath
    $exportDir = Split-Path -Parent $exportFullPath
    if (-not (Test-Path $exportDir)) {
        New-Item -ItemType Directory -Path $exportDir | Out-Null
    }

    $body = @{
        objects = @(
            @{ type = "dashboard"; id = "oscorp-phase32-operational" },
            @{ type = "dashboard"; id = "oscorp-phase33-analytics" },
            @{ type = "index-pattern"; id = $script:EventsDataViewId },
            @{ type = "index-pattern"; id = $script:RiskDataViewId }
        )
        includeReferencesDeep = $true
        excludeExportDetails = $true
    }

    Invoke-WebRequest `
        -Method Post `
        -Uri "$KibanaUrl/api/saved_objects/_export" `
        -Headers $Headers `
        -ContentType "application/json" `
        -Body (ConvertTo-Json -InputObject $body -Depth 20) `
        -OutFile $exportFullPath `
        -TimeoutSec 60

    Write-Host "[kibana:fase33] Export listo: $exportFullPath"
}

Write-Host "[kibana:fase33] Verificando Kibana..."
$status = Invoke-KibanaJson -Method "Get" -Path "/api/status"
if ($status.status.overall.level -ne "available") {
    throw "Kibana no esta disponible: $($status.status.overall.level)"
}

Ensure-EventsGeoMapping
Ensure-RiskIndex
Sync-RiskIndex

$script:EventsDataViewId = Get-OrCreateDataView -Title $EventsIndexName -Name "OSCORP Cowrie Events" -TimeField "timestamp_evento"
$script:RiskDataViewId = Get-OrCreateDataView -Title $RiskIndexName -Name "OSCORP Session Risk" -TimeField "last_event_at"

Set-RiskVisualizations -RiskDataViewId $script:RiskDataViewId
Set-HighRiskSearch -RiskDataViewId $script:RiskDataViewId
Set-AttackOriginMap -EventsDataViewId $script:EventsDataViewId
Set-AnalyticsDashboard
Export-Dashboards

Write-Host "[kibana:fase33] Configuracion completada."
Write-Host "[kibana:fase33] Abrir: $KibanaUrl/app/dashboards#/view/oscorp-phase33-analytics"
