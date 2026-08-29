from pathlib import Path

import fitz

root = Path('/mnt/c/Users/gordo/Documents/Github/PythonScripts/Foreground Masking/documentation/qa_clean22_flow')
document = fitz.open(root / 'clean22_flow_qa.pdf')
for number, page in enumerate(document, 1):
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    pixmap.save(root / f'page-{number}.png')
print(len(document))
