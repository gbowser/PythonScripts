# Render Word documents on Windows

The existing helper is now `tools/document_rendering/render_docx_windows.ps1`.
It still uses the repository Python environment and the installed LibreOffice,
Poppler and Codex document renderer. The current renderer path is configured
inside the helper and may need updating after a Codex plugin upgrade.

From the PythonScripts root:

```powershell
uv pip install -r .\tools\document_rendering\requirements.txt
powershell.exe -NoProfile -File .\tools\document_rendering\render_docx_windows.ps1 -InputPath "Euclid\Codex Documentation\Astronomy_Programs_Catalogue.docx" -EmitPdf
```

Without an explicit `-OutputDirectory`, previews go under
`D:\Dropbox\Public Documents\UCLAN\MSc Research\Repository_maintenance\Document_previews\<document name>`. An unavailable Dropbox research folder is not replaced by a
C: output location. The helper needs a working LibreOffice/Poppler installation;
moving it does not install or change those applications.
