# Enrolled Faces Directory

This directory stores face crops organized by person name (e.g. `database/faces/<PersonName>/<image>.jpg`).

- In local development, enrolling faces via the desktop UI or Flutter mobile app automatically creates person subfolders here.
- In production, face crops are securely synchronized to private cloud storage (Supabase Storage / S3) and kept out of version control.
