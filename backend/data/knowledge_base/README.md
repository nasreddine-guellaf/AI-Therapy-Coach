# Fixed knowledge base

Place exactly **3 trusted, text-based PDF files** in this directory before
running the ingestion command.

These files form the fixed internal knowledge base used by every assistant
conversation. They are selected and maintained by the project owner or an
authorized administrator; application users do not upload documents.

Scanned PDFs and image-only PDFs are not supported because OCR is not
implemented yet.

Real PDF files should not be committed to Git unless their license explicitly
allows redistribution. The repository ignores every PDF in this directory.

