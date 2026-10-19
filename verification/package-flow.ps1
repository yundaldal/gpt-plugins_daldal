param([switch]$Rebuild)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$root=Split-Path $PSScriptRoot -Parent
$ids=@('approval-excel','canva-game','ib-core','ib-planner','iep-eval','iep-plan','related-document-extractor')
foreach($id in $ids) {
  $source=Join-Path $root "plugins/$id"
  $zipPath=Join-Path $root "downloads/$id.zip"
  if($Rebuild) {
    # Replace only the seven explicitly listed distribution archives.
    $stream=[IO.File]::Open($zipPath,[IO.FileMode]::Create)
    $archive=[IO.Compression.ZipArchive]::new($stream,[IO.Compression.ZipArchiveMode]::Create)
    try {
      Get-ChildItem -LiteralPath $source -Recurse -File -Force | Sort-Object FullName | ForEach-Object {
        $relative=$_.FullName.Substring($source.Length+1).Replace('\','/')
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive,$_.FullName,$relative,[IO.Compression.CompressionLevel]::Optimal) | Out-Null
      }
    } finally { $archive.Dispose(); $stream.Dispose() }
  }
  $archive=[IO.Compression.ZipFile]::OpenRead($zipPath)
  try {
    $files=@(Get-ChildItem -LiteralPath $source -Recurse -File -Force)
    if($archive.Entries.Count -ne $files.Count) { throw "$id file count mismatch" }
    foreach($file in $files) {
      $relative=$file.FullName.Substring($source.Length+1).Replace('\','/')
      $entry=$archive.GetEntry($relative)
      if(-not $entry) { throw "Missing $id/$relative" }
      $entryStream=$entry.Open(); $hash=[Security.Cryptography.SHA256]::Create()
      try { $actual=[BitConverter]::ToString($hash.ComputeHash($entryStream)).Replace('-','') }
      finally { $entryStream.Dispose(); $hash.Dispose() }
      if($actual -ne (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash) { throw "Bytes differ: $id/$relative" }
    }
    Write-Output ("PASS {0}: {1} files match source; ZIP SHA256 {2}" -f $id,$files.Count,(Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash)
  } finally { $archive.Dispose() }
}
