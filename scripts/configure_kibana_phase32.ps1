param(
    [string]$KibanaUrl = "http://localhost:5601",
    [string]$ElasticsearchUrl = "http://localhost:9200",
    [string]$IndexName = "cowrie-events",
    [string]$TimeField = "timestamp_evento"
)

$ErrorActionPreference = "Stop"

$Headers = @{
    "kbn-xsrf" = "oscorp-phase32"
}

function ConvertTo-CompactJson {
    param([Parameter(Mandatory = $true)]$Value)
    return ConvertTo-Json -InputObject $Value -Depth 50 -Compress
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
        -Body (ConvertTo-Json -InputObject $Body -Depth 50) `
        -TimeoutSec 30
}

function Assert-ElasticsearchIndex {
    Write-Host "[kibana:fase32] Verificando indice $IndexName en Elasticsearch..."
    $count = Invoke-RestMethod -Uri "$ElasticsearchUrl/$IndexName/_count" -TimeoutSec 30
    if ($count.count -lt 1) {
        throw "El indice $IndexName no tiene documentos. Ejecute el pipeline antes de crear dashboards."
    }

    $mapping = Invoke-RestMethod -Uri "$ElasticsearchUrl/$IndexName/_mapping" -TimeoutSec 30
    $properties = $mapping.$IndexName.mappings.properties
    foreach ($field in @($TimeField, "eventid", "session_id", "src_ip", "username")) {
        if (-not $properties.PSObject.Properties.Name.Contains($field)) {
            throw "El campo requerido '$field' no existe en el mapping de $IndexName."
        }
    }

    Write-Host "[kibana:fase32] Documentos disponibles: $($count.count)"
}

function Get-OrCreateDataView {
    Write-Host "[kibana:fase32] Configurando data view $IndexName..."
    $encodedIndex = [System.Uri]::EscapeDataString($IndexName)
    $result = Invoke-KibanaJson -Method "Get" -Path "/api/saved_objects/_find?type=index-pattern&search_fields=title&search=$encodedIndex&per_page=100"
    $existing = @($result.saved_objects) | Where-Object { $_.attributes.title -eq $IndexName } | Select-Object -First 1
    if ($existing) {
        Write-Host "[kibana:fase32] Data view existente: $($existing.id)"
        return $existing.id
    }

    $body = @{
        data_view = @{
            title = $IndexName
            name = "OSCORP Cowrie Events"
            timeFieldName = $TimeField
        }
        override = $true
    }
    $created = Invoke-KibanaJson -Method "Post" -Path "/api/data_views/data_view" -Body $body
    Write-Host "[kibana:fase32] Data view creado: $($created.data_view.id)"
    return $created.data_view.id
}

function New-SearchSource {
    param(
        [Parameter(Mandatory = $true)][string]$DataViewId,
        [string]$Query = ""
    )

    return @{
        query = @{
            language = "kuery"
            query = $Query
        }
        filter = @()
        indexRefName = "kibanaSavedObjectMeta.searchSourceJSON.index"
    }
}

function Set-Visualization {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)]$VisState,
        [Parameter(Mandatory = $true)][string]$DataViewId
    )

    $body = @{
        attributes = @{
            title = $Title
            description = $Description
            visState = ConvertTo-CompactJson $VisState
            uiStateJSON = "{}"
            kibanaSavedObjectMeta = @{
                searchSourceJSON = ConvertTo-CompactJson (New-SearchSource -DataViewId $DataViewId)
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
    Write-Host "[kibana:fase32] Visualizacion lista: $Title"
}

function Set-SavedSearch {
    param(
        [Parameter(Mandatory = $true)][string]$DataViewId
    )

    $searchSource = New-SearchSource -DataViewId $DataViewId
    $searchSource.sort = @(
        @{
            $TimeField = @{
                order = "desc"
                unmapped_type = "boolean"
            }
        }
    )

    $body = @{
        attributes = @{
            title = "OSCORP - Eventos operativos"
            description = "Tabla operativa de eventos Cowrie con campos principales para filtrado."
            columns = @($TimeField, "eventid", "src_ip", "username", "session_id", "command_input", "url", "shasum", "sensor")
            sort = @(@($TimeField, "desc"))
            kibanaSavedObjectMeta = @{
                searchSourceJSON = ConvertTo-CompactJson $searchSource
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

    Invoke-KibanaJson -Method "Post" -Path "/api/saved_objects/search/oscorp-phase32-operational-events`?overwrite=true" -Body $body | Out-Null
    Write-Host "[kibana:fase32] Tabla operativa lista: OSCORP - Eventos operativos"
}

function Set-Visualizations {
    param([Parameter(Mandatory = $true)][string]$DataViewId)

    Set-Visualization `
        -Id "oscorp-phase32-total-events" `
        -Title "OSCORP - Eventos totales" `
        -Description "Total de eventos en la ventana temporal del dashboard." `
        -DataViewId $DataViewId `
        -VisState @{
            title = "OSCORP - Eventos totales"
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
                        subText = "eventos"
                        fontSize = 60
                    }
                }
            }
            aggs = @(
                @{
                    id = "1"
                    enabled = $true
                    type = "count"
                    schema = "metric"
                    params = @{}
                }
            )
        }

    Set-Visualization `
        -Id "oscorp-phase32-events-timeline" `
        -Title "OSCORP - Evolucion temporal de eventos" `
        -Description "Histograma de eventos Cowrie por intervalo temporal." `
        -DataViewId $DataViewId `
        -VisState @{
            title = "OSCORP - Evolucion temporal de eventos"
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
                        labels = @{ show = $true; truncate = 100 }
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
                        title = @{ text = "Eventos" }
                    }
                )
                seriesParams = @(
                    @{
                        show = $true
                        type = "histogram"
                        mode = "normal"
                        data = @{ label = "Eventos"; id = "1" }
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
                @{
                    id = "1"
                    enabled = $true
                    type = "count"
                    schema = "metric"
                    params = @{}
                },
                @{
                    id = "2"
                    enabled = $true
                    type = "date_histogram"
                    schema = "segment"
                    params = @{
                        field = $TimeField
                        timeRange = @{ from = "now-24h"; to = "now" }
                        useNormalizedEsInterval = $true
                        interval = "auto"
                        drop_partials = $false
                        min_doc_count = 1
                        extended_bounds = @{}
                    }
                }
            )
        }

    Set-Visualization `
        -Id "oscorp-phase32-events-by-type" `
        -Title "OSCORP - Eventos por tipo" `
        -Description "Distribucion de eventos Cowrie por eventid." `
        -DataViewId $DataViewId `
        -VisState @{
            title = "OSCORP - Eventos por tipo"
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
                        labels = @{ show = $true; filter = $false; truncate = 120 }
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
                        title = @{ text = "Eventos" }
                    }
                )
                seriesParams = @(
                    @{
                        show = $true
                        type = "histogram"
                        mode = "normal"
                        data = @{ label = "Eventos"; id = "1" }
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
                @{
                    id = "1"
                    enabled = $true
                    type = "count"
                    schema = "metric"
                    params = @{}
                },
                @{
                    id = "2"
                    enabled = $true
                    type = "terms"
                    schema = "segment"
                    params = @{
                        field = "eventid"
                        orderBy = "1"
                        order = "desc"
                        size = 10
                        otherBucket = $false
                        missingBucket = $false
                    }
                }
            )
        }

    Set-Visualization `
        -Id "oscorp-phase32-sessions-table" `
        -Title "OSCORP - Sesiones activas por eventos" `
        -Description "Tabla de sesiones Cowrie ordenadas por volumen de eventos." `
        -DataViewId $DataViewId `
        -VisState @{
            title = "OSCORP - Sesiones activas por eventos"
            type = "table"
            params = @{
                perPage = 10
                showPartialRows = $false
                showMetricsAtAllLevels = $false
                sort = @{ columnIndex = $null; direction = $null }
                showTotal = $false
                totalFunc = "sum"
            }
            aggs = @(
                @{
                    id = "1"
                    enabled = $true
                    type = "count"
                    schema = "metric"
                    params = @{}
                },
                @{
                    id = "2"
                    enabled = $true
                    type = "terms"
                    schema = "bucket"
                    params = @{
                        field = "session_id"
                        orderBy = "1"
                        order = "desc"
                        size = 15
                        otherBucket = $false
                        missingBucket = $false
                    }
                },
                @{
                    id = "3"
                    enabled = $true
                    type = "terms"
                    schema = "bucket"
                    params = @{
                        field = "src_ip"
                        orderBy = "1"
                        order = "desc"
                        size = 5
                        otherBucket = $false
                        missingBucket = $false
                    }
                }
            )
        }

    Set-Visualization `
        -Id "oscorp-phase32-src-ip-table" `
        -Title "OSCORP - IPs origen principales" `
        -Description "Tabla de IPs origen con volumen de eventos para filtros operativos." `
        -DataViewId $DataViewId `
        -VisState @{
            title = "OSCORP - IPs origen principales"
            type = "table"
            params = @{
                perPage = 10
                showPartialRows = $false
                showMetricsAtAllLevels = $false
                sort = @{ columnIndex = $null; direction = $null }
                showTotal = $false
                totalFunc = "sum"
            }
            aggs = @(
                @{
                    id = "1"
                    enabled = $true
                    type = "count"
                    schema = "metric"
                    params = @{}
                },
                @{
                    id = "2"
                    enabled = $true
                    type = "terms"
                    schema = "bucket"
                    params = @{
                        field = "src_ip"
                        orderBy = "1"
                        order = "desc"
                        size = 15
                        otherBucket = $false
                        missingBucket = $false
                    }
                }
            )
        }
}

function Set-Dashboard {
    $panelDefinitions = @(
        @{ name = "panel_1"; type = "visualization"; id = "oscorp-phase32-total-events"; x = 0; y = 0; w = 12; h = 8 },
        @{ name = "panel_2"; type = "visualization"; id = "oscorp-phase32-events-timeline"; x = 12; y = 0; w = 24; h = 8 },
        @{ name = "panel_3"; type = "visualization"; id = "oscorp-phase32-events-by-type"; x = 36; y = 0; w = 12; h = 8 },
        @{ name = "panel_4"; type = "visualization"; id = "oscorp-phase32-sessions-table"; x = 0; y = 8; w = 24; h = 12 },
        @{ name = "panel_5"; type = "visualization"; id = "oscorp-phase32-src-ip-table"; x = 24; y = 8; w = 24; h = 12 },
        @{ name = "panel_6"; type = "search"; id = "oscorp-phase32-operational-events"; x = 0; y = 20; w = 48; h = 14 }
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
            title = "OSCORP - Dashboard operativo"
            description = "Fase 32 - eventos, sesiones, evolucion temporal y tablas operativas sobre cowrie-events."
            panelsJSON = ConvertTo-CompactJson -Value $panels
            optionsJSON = ConvertTo-CompactJson @{
                useMargins = $true
                syncColors = $false
                syncCursor = $true
                syncTooltips = $true
                hidePanelTitles = $false
            }
            timeRestore = $true
            timeFrom = "now-24h"
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

    Invoke-KibanaJson -Method "Post" -Path "/api/saved_objects/dashboard/oscorp-phase32-operational`?overwrite=true" -Body $body | Out-Null
    Write-Host "[kibana:fase32] Dashboard listo: OSCORP - Dashboard operativo"
}

Write-Host "[kibana:fase32] Verificando Kibana..."
$status = Invoke-KibanaJson -Method "Get" -Path "/api/status"
if ($status.status.overall.level -ne "available") {
    throw "Kibana no esta disponible: $($status.status.overall.level)"
}

Assert-ElasticsearchIndex
$dataViewId = Get-OrCreateDataView
Set-Visualizations -DataViewId $dataViewId
Set-SavedSearch -DataViewId $dataViewId
Set-Dashboard

Write-Host "[kibana:fase32] Configuracion completada."
Write-Host "[kibana:fase32] Abrir: $KibanaUrl/app/dashboards#/view/oscorp-phase32-operational"
