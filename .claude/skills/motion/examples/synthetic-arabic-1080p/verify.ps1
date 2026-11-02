param([Parameter(Mandatory = $true)][string]$MiyaarRoot)
$ErrorActionPreference = 'Stop'
$motionRenderer = Join-Path $MiyaarRoot '.claude/skills/motion/render.mjs'
$motionSpec = Join-Path $PSScriptRoot 'smoke-reviewed.json'
$motionVideo = Join-Path $PSScriptRoot 'smoke-reviewed.mp4'
if (-not (Test-Path -LiteralPath $motionRenderer -PathType Leaf)) { throw 'Existing Motion renderer not found' }
node $motionRenderer $motionSpec --check
if ($LASTEXITCODE -ne 0) { throw 'Motion spec/source validation failed' }
$probeText = ffprobe -v error -show_streams -show_format -of json $motionVideo
if ($LASTEXITCODE -ne 0) { throw 'ffprobe failed' }
$media = ($probeText -join "`n") | ConvertFrom-Json
$videoStreams = @($media.streams | Where-Object codec_type -eq 'video')
$audioStreams = @($media.streams | Where-Object codec_type -eq 'audio')
if ($videoStreams.Count -ne 1 -or $audioStreams.Count -ne 0) { throw 'Unexpected streams' }
$videoStream = $videoStreams[0]
if ($videoStream.width -ne 1920 -or $videoStream.height -ne 1080 -or
    $videoStream.codec_name -ne 'h264' -or $videoStream.pix_fmt -ne 'yuv420p' -or
    $videoStream.avg_frame_rate -ne '30/1' -or [int]$videoStream.nb_frames -ne 120 -or
    [double]::Parse($media.format.duration, [Globalization.CultureInfo]::InvariantCulture) -ne 4.0) {
    throw 'Synthetic MP4 differs from the verified contract'
}
ffmpeg -hide_banner -loglevel error -nostdin -threads 2 -i $motionVideo -f null -
if ($LASTEXITCODE -ne 0) { throw 'Video decode failed' }
Write-Output 'PASS: sourced fixture and existing silent 1080p MP4 verified; no new render or agent invocation.'
